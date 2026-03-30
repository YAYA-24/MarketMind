"""
微信 ClawBot 扫码登录。

流程：
  1. 调 ilink API 获取二维码
  2. 在终端渲染 QR 码
  3. 轮询等待用户扫码确认
  4. 保存 bot_token 到本地

使用:
  python -m wechat.auth
"""

import json
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from .client import DEFAULT_BASE_URL, save_account, CREDENTIALS_FILE

BOT_TYPE = "3"
LOGIN_TIMEOUT_S = 480
STATUS_POLL_TIMEOUT_S = 35


def _fetch_json(url: str, headers: dict | None = None, timeout_s: float = 15) -> dict:
    req = urllib.request.Request(url=url, method="GET", headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _render_qr_terminal(content: str):
    """在终端渲染二维码。"""
    try:
        import qrcode
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=1, border=1)
        qr.add_data(content)
        qr.make(fit=True)
        qr.print_ascii(invert=True)
        return True
    except ImportError:
        pass

    print("提示: 安装 qrcode 可获得更好的显示效果: pip install qrcode[pil]")
    print(f"\n请复制以下内容到二维码生成器扫码:\n{content}\n")
    return False


def _fetch_qr_code(base_url: str) -> dict:
    return _fetch_json(f"{base_url}/ilink/bot/get_bot_qrcode?bot_type={BOT_TYPE}")


def _poll_qr_status(base_url: str, qrcode_id: str) -> dict:
    encoded = urllib.parse.quote(qrcode_id, safe="")
    url = f"{base_url}/ilink/bot/get_qrcode_status?qrcode={encoded}"
    try:
        return _fetch_json(
            url,
            headers={"iLink-App-ClientVersion": "1"},
            timeout_s=STATUS_POLL_TIMEOUT_S,
        )
    except (TimeoutError, socket.timeout, urllib.error.URLError) as err:
        reason = getattr(err, "reason", err)
        if isinstance(reason, (TimeoutError, socket.timeout)):
            return {"status": "wait"}
        raise


def login(base_url: str | None = None):
    """执行扫码登录流程。"""
    base_url = base_url or DEFAULT_BASE_URL

    print("正在获取微信登录二维码...\n")
    qr_response = _fetch_qr_code(base_url)

    qr_content = qr_response.get("qrcode_img_content")
    if not qr_content:
        print("二维码内容缺失，请稍后重试。")
        sys.exit(1)

    _render_qr_terminal(qr_content)
    print("\n请使用微信扫描上方二维码并确认登录。\n")

    deadline = time.time() + LOGIN_TIMEOUT_S
    scanned_printed = False

    while time.time() < deadline:
        status = _poll_qr_status(base_url, qr_response["qrcode"])
        current = status.get("status")

        if current == "wait":
            sys.stdout.write(".")
            sys.stdout.flush()
        elif current == "scaned":
            if not scanned_printed:
                print("\n已扫码，请在微信中确认...")
                scanned_printed = True
        elif current == "expired":
            print("\n二维码已过期，请重新运行。")
            sys.exit(1)
        elif current == "confirmed":
            if not status.get("ilink_bot_id") or not status.get("bot_token"):
                print("\n登录失败：服务端未返回完整凭据。")
                sys.exit(1)

            account = {
                "token": status["bot_token"],
                "baseUrl": status.get("baseurl") or base_url,
                "accountId": status["ilink_bot_id"],
                "userId": status.get("ilink_user_id"),
            }
            save_account(account)

            print(f"\n微信连接成功!")
            print(f"  账号 ID: {account['accountId']}")
            print(f"  凭据已保存到: {CREDENTIALS_FILE}")
            print(f"\n现在可以运行 `python -m wechat.bot` 启动微信 bot。")
            return

        time.sleep(1)

    print("\n登录超时，请重新运行。")
    sys.exit(1)


if __name__ == "__main__":
    login()
