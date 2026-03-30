"""
微信 A 股分析 Bot 主循环。

长轮询接收微信消息 -> 调用 LangGraph Agent -> 回复文本和K线图。
同时启动定时线程，每天 9:00 推送激光雷达企业资讯。

启动:
  python -m wechat.bot
"""

import asyncio
import os
import re
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from langchain_core.messages import HumanMessage, AIMessage

from src.agent.graph import build_graph, _normalize_messages, _flatten_tool_content
from src.config.settings import CHART_DIR

from wechat.client import WechatClient, extract_text, load_account, save_push_target
from wechat.daily_push import run_daily_push

MAX_REPLY_LEN = 2000
MAX_CONSECUTIVE_FAILURES = 5
RETRY_DELAY_S = 2
BACKOFF_DELAY_S = 30

DAILY_PUSH_HOUR = 9
DAILY_PUSH_MINUTE = 0


def _log(msg: str):
    ts = time.strftime("%H:%M:%S")
    sys.stderr.write(f"[{ts}] [wechat-bot] {msg}\n")
    sys.stderr.flush()


def _extract_chart_images(text: str) -> list[str]:
    """从 Agent 回复中提取 K 线图文件路径。"""
    images = []
    for match in re.findall(r'[\w/._-]+\.png', text):
        filename = os.path.basename(match.strip('`').strip())
        chart_path = CHART_DIR / filename
        if chart_path.exists():
            images.append(str(chart_path))
    return images


def _strip_image_paths(text: str) -> str:
    """移除回复文本中的图片路径（微信里会单独发图）。"""
    return re.sub(r'`?[\w/._-]+\.png`?', '', text).strip()


class AgentRunner:
    """管理 Agent 实例和每个用户的会话历史。"""

    def __init__(self):
        self._agent = build_graph(mcp_tools=None)
        self._sessions: dict[str, list] = {}
        _log(f"Agent 已初始化，工具数量: {len(self._agent.nodes) if hasattr(self._agent, 'nodes') else '?'}")

    async def run(self, user_id: str, text: str) -> tuple[str, list[str]]:
        """运行 Agent 并返回 (回复文本, K线图路径列表)。"""
        if user_id not in self._sessions:
            self._sessions[user_id] = []

        messages = self._sessions[user_id]
        messages.append(HumanMessage(content=text))

        full_chunks: list[str] = []
        try:
            async for msg, metadata in self._agent.astream(
                {"messages": messages},
                stream_mode="messages",
            ):
                node = metadata.get("langgraph_node", "")
                if (
                    isinstance(msg, AIMessage)
                    and not msg.tool_calls
                    and msg.content
                    and node == "chatbot"
                ):
                    full_chunks.append(msg.content)
        except Exception as err:
            _log(f"Agent 执行出错: {err}")
            return f"抱歉，处理时出错了: {err}", []

        full_content = "".join(full_chunks)
        messages.append(AIMessage(content=full_content))

        # 限制会话长度，避免内存膨胀
        if len(messages) > 40:
            self._sessions[user_id] = messages[-20:]

        images = _extract_chart_images(full_content)
        reply_text = _strip_image_paths(full_content) if images else full_content

        return reply_text, images


def _seconds_until(hour: int, minute: int) -> float:
    """计算从现在到下一个 hour:minute 的秒数。"""
    now = datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


def _scheduler_loop(stop_event: threading.Event):
    """定时推送线程：每天 DAILY_PUSH_HOUR:DAILY_PUSH_MINUTE 执行一次推送。"""
    _log(f"定时推送线程已启动，每天 {DAILY_PUSH_HOUR:02d}:{DAILY_PUSH_MINUTE:02d} 推送激光雷达早报。")
    while not stop_event.is_set():
        wait_s = _seconds_until(DAILY_PUSH_HOUR, DAILY_PUSH_MINUTE)
        _log(f"下次推送在 {wait_s/3600:.1f} 小时后")
        if stop_event.wait(timeout=wait_s):
            break
        try:
            _log("定时推送触发 →")
            run_daily_push(dry_run=False)
        except Exception as e:
            _log(f"定时推送失败: {e}")


def _handle_command(text: str, sender_id: str, context_token: str, client: WechatClient) -> str | None:
    """处理斜杠命令。返回回复文本，如果不是命令则返回 None。"""
    stripped = text.strip()
    if stripped == "/push":
        _log(f"手动触发推送 (by {sender_id[:12]})")
        try:
            report = run_daily_push(dry_run=True)
            return report
        except Exception as e:
            return f"推送生成失败: {e}"
    if stripped == "/pushall":
        _log(f"手动触发全员推送 (by {sender_id[:12]})")
        threading.Thread(
            target=run_daily_push, kwargs={"dry_run": False}, daemon=True
        ).start()
        return "已触发全员推送，请稍等..."
    return None


def main():
    account = load_account()
    if not account:
        print("未找到微信登录凭据。请先运行:")
        print("  python -m wechat.auth")
        sys.exit(1)

    _log(f"使用账号: {account.get('accountId', 'env')}")

    client = WechatClient()
    runner = AgentRunner()
    loop = asyncio.new_event_loop()

    stop_event = threading.Event()
    scheduler_thread = threading.Thread(
        target=_scheduler_loop, args=(stop_event,), daemon=True
    )
    scheduler_thread.start()

    get_updates_buf = ""
    consecutive_failures = 0

    _log("开始监听微信消息... (Ctrl+C 退出)")

    while True:
        try:
            response = client.get_updates(get_updates_buf)

            is_error = (
                ("ret" in response and response.get("ret") not in (None, 0))
                or ("errcode" in response and response.get("errcode") not in (None, 0))
            )
            if is_error:
                consecutive_failures += 1
                errmsg = response.get("errmsg") or ""
                _log(f"getUpdates 失败: ret={response.get('ret')} errcode={response.get('errcode')} errmsg={errmsg}")
                if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    _log(f"连续失败 {MAX_CONSECUTIVE_FAILURES} 次，等待 {BACKOFF_DELAY_S}s...")
                    consecutive_failures = 0
                    time.sleep(BACKOFF_DELAY_S)
                else:
                    time.sleep(RETRY_DELAY_S)
                continue

            consecutive_failures = 0

            if response.get("get_updates_buf"):
                get_updates_buf = response["get_updates_buf"]

            for msg in response.get("msgs") or []:
                if msg.get("message_type") != 1:
                    continue

                text = extract_text(msg)
                if not text:
                    continue

                sender_id = msg.get("from_user_id") or "unknown"
                context_token = msg.get("context_token")
                sender_short = sender_id.split("@")[0][:12]

                _log(f"收到消息: from={sender_short} text={text[:60]}")

                if not context_token:
                    _log(f"缺少 context_token，无法回复 {sender_short}")
                    continue

                save_push_target(sender_id, context_token)

                # 检查是否为斜杠命令
                cmd_reply = _handle_command(text, sender_id, context_token, client)
                if cmd_reply is not None:
                    for i in range(0, len(cmd_reply), MAX_REPLY_LEN):
                        try:
                            client.send_message(sender_id, context_token, cmd_reply[i:i + MAX_REPLY_LEN])
                        except Exception as err:
                            _log(f"发送命令回复失败: {err}")
                    _log(f"命令已回复 {sender_short}: {len(cmd_reply)}字")
                    continue

                # 发送"正在分析"提示
                client.send_typing(sender_id, context_token)

                # 在异步 loop 中运行 Agent
                try:
                    reply_text, images = loop.run_until_complete(
                        runner.run(sender_id, text)
                    )
                except Exception as err:
                    _log(f"Agent 运行失败: {err}")
                    reply_text = f"处理失败: {err}"
                    images = []

                # 发送文本回复（拆分长文本）
                if reply_text:
                    for i in range(0, len(reply_text), MAX_REPLY_LEN):
                        chunk = reply_text[i:i + MAX_REPLY_LEN]
                        try:
                            client.send_message(sender_id, context_token, chunk)
                        except Exception as err:
                            _log(f"发送文本失败: {err}")

                # 发送 K 线图（如果有）
                for img_path in images:
                    _log(f"K线图待发送: {img_path} (图片发送需要 CDN 上传，当前仅支持文本)")

                _log(f"已回复 {sender_short}: {len(reply_text)}字 {len(images)}张图")

        except KeyboardInterrupt:
            _log("收到退出信号，停止监听。")
            stop_event.set()
            break
        except Exception as err:
            consecutive_failures += 1
            _log(f"轮询异常: {err}")
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                consecutive_failures = 0
                time.sleep(BACKOFF_DELAY_S)
            else:
                time.sleep(RETRY_DELAY_S)

    loop.close()


if __name__ == "__main__":
    main()
