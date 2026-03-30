"""
微信 ilink API 客户端。

基于 ClawBot 的 ilink 协议与微信通信：
  - get_updates: 长轮询接收新消息
  - send_message: 发送文本回复
  - send_image:   发送图片（K线图等）

参考: https://github.com/sitarua/wechat-agent-channel
"""

import json
import os
import socket
import time
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_BASE_URL = "https://ilinkai.weixin.qq.com"
CHANNEL_VERSION = "1.0.0"
LONG_POLL_TIMEOUT_S = 40
SEND_TIMEOUT_S = 15

STATE_DIR = Path(
    os.environ.get("WECHAT_BOT_STATE_DIR", "").strip()
    or (Path.home() / ".marketmind-wechat")
)
CREDENTIALS_FILE = STATE_DIR / "account.json"
PUSH_TARGETS_FILE = STATE_DIR / "push_targets.json"


def _load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_account() -> dict | None:
    """从环境变量或本地文件加载 ClawBot 登录凭据。"""
    env_token = os.environ.get("BOT_TOKEN", "").strip()
    if env_token:
        return {
            "token": env_token,
            "baseUrl": os.environ.get("WECHAT_BASE_URL", "").strip() or DEFAULT_BASE_URL,
        }

    parsed = _load_json(CREDENTIALS_FILE)
    if not isinstance(parsed, dict):
        return None

    token = str(parsed.get("token") or "").strip()
    if not token:
        return None

    return {
        "token": token,
        "baseUrl": str(parsed.get("baseUrl") or "").strip() or DEFAULT_BASE_URL,
        "accountId": parsed.get("accountId"),
    }


def save_account(account: dict):
    """保存 ClawBot 登录凭据到本地文件。"""
    CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    CREDENTIALS_FILE.write_text(
        json.dumps(account, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    try:
        os.chmod(CREDENTIALS_FILE, 0o600)
    except Exception:
        pass


class WechatClient:
    """微信 ilink API 客户端。"""

    def __init__(self):
        self._account: dict | None = None

    def _get_account(self) -> dict:
        self._account = load_account()
        if not self._account or not self._account.get("token"):
            raise RuntimeError(
                "未找到微信登录凭据。请先运行 `python -m wechat.auth` 扫码登录，"
                "或设置环境变量 BOT_TOKEN。"
            )
        return self._account

    def _build_headers(self, body_bytes: bytes) -> dict:
        account = self._get_account()
        return {
            "Content-Type": "application/json",
            "AuthorizationType": "ilink_bot_token",
            "Authorization": f"Bearer {account['token']}",
            "Content-Length": str(len(body_bytes)),
        }

    def _post_json(self, url: str, payload: dict, timeout_s: float) -> dict:
        body = json.dumps(payload, ensure_ascii=False)
        body_bytes = body.encode("utf-8")
        req = urllib.request.Request(
            url=url,
            method="POST",
            data=body_bytes,
            headers=self._build_headers(body_bytes),
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw)
        except urllib.error.HTTPError as err:
            detail = ""
            try:
                detail = err.read().decode("utf-8", errors="replace")[:300]
            except Exception:
                pass
            raise RuntimeError(f"HTTP {err.code}: {detail}") from err

    @staticmethod
    def _check_response(action: str, response: dict):
        ret = response.get("ret")
        errcode = response.get("errcode")
        if ret in (None, 0) and errcode in (None, 0):
            return
        errmsg = response.get("errmsg") or response.get("msg") or ""
        raise RuntimeError(f"{action} 失败: ret={ret} errcode={errcode} errmsg={errmsg}")

    def get_updates(self, buf: str = "") -> dict:
        """长轮询获取新消息。返回 {'msgs': [...], 'get_updates_buf': '...'}"""
        account = self._get_account()
        payload = {
            "get_updates_buf": buf,
            "base_info": {"channel_version": CHANNEL_VERSION},
        }
        try:
            response = self._post_json(
                f"{account['baseUrl']}/ilink/bot/getupdates",
                payload,
                timeout_s=LONG_POLL_TIMEOUT_S,
            )
            self._check_response("getUpdates", response)
            return response
        except (TimeoutError, socket.timeout, urllib.error.URLError) as err:
            reason = getattr(err, "reason", err)
            if isinstance(reason, (TimeoutError, socket.timeout)):
                return {"ret": 0, "msgs": [], "get_updates_buf": buf}
            raise

    def send_message(self, to_user_id: str, context_token: str, text: str) -> dict:
        """发送文本消息到微信。"""
        account = self._get_account()
        client_id = f"marketmind:{int(time.time() * 1000)}"
        payload = {
            "msg": {
                "from_user_id": "",
                "to_user_id": to_user_id,
                "client_id": client_id,
                "message_type": 2,
                "message_state": 2,
                "item_list": [
                    {"type": 1, "text_item": {"text": text}},
                ],
                "context_token": context_token,
            },
            "base_info": {"channel_version": CHANNEL_VERSION},
        }
        response = self._post_json(
            f"{account['baseUrl']}/ilink/bot/sendmessage",
            payload,
            timeout_s=SEND_TIMEOUT_S,
        )
        self._check_response("sendMessage", response)
        return response

    def send_typing(self, to_user_id: str, context_token: str):
        """发送"正在输入"状态提示。"""
        account = self._get_account()
        client_id = f"marketmind:{int(time.time() * 1000)}"
        payload = {
            "msg": {
                "from_user_id": "",
                "to_user_id": to_user_id,
                "client_id": client_id,
                "message_type": 2,
                "message_state": 1,  # PARTIAL = 正在输入
                "item_list": [
                    {"type": 1, "text_item": {"text": "正在分析..."}},
                ],
                "context_token": context_token,
            },
            "base_info": {"channel_version": CHANNEL_VERSION},
        }
        try:
            self._post_json(
                f"{account['baseUrl']}/ilink/bot/sendmessage",
                payload,
                timeout_s=SEND_TIMEOUT_S,
            )
        except Exception:
            pass


def save_push_target(user_id: str, context_token: str):
    """持久化保存推送目标（user_id + context_token），供定时主动推送使用。"""
    targets = load_push_targets()
    targets[user_id] = {
        "context_token": context_token,
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    PUSH_TARGETS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PUSH_TARGETS_FILE.write_text(
        json.dumps(targets, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_push_targets() -> dict:
    """加载所有推送目标。返回 {user_id: {context_token, updated_at}}。"""
    data = _load_json(PUSH_TARGETS_FILE)
    return data if isinstance(data, dict) else {}


def extract_text(msg: dict) -> str:
    """从 ilink 消息体中提取文本内容。"""
    for item in msg.get("item_list") or []:
        if item.get("type") == 1:
            text_item = item.get("text_item") or {}
            text = text_item.get("text")
            if text:
                ref = item.get("ref_msg")
                if ref:
                    title = ref.get("title", "")
                    return f"[引用: {title}]\n{text}" if title else text
                return text
        if item.get("type") == 3:
            voice_item = item.get("voice_item") or {}
            if voice_item.get("text"):
                return voice_item["text"]
    return ""
