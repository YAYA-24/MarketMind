"""
每日激光雷达企业资讯推送。

功能：
  1. 获取禾赛科技 (HSAI) 和速腾聚创 (2498.HK) 的行情快照
  2. 通过 Tavily 搜索两家公司的最新资讯 + 行业动态
  3. 格式化为微信文本消息
  4. 通过 ilink API 推送给所有已注册用户

用法:
  手动测试（仅生成不发送）:  python -m wechat.daily_push --dry-run
  手动推送:                  python -m wechat.daily_push
"""

import os
import sys
import time
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from src.global_quote import fetch_all_watched, WATCHED_STOCKS
from src.config.settings import TAVILY_API_KEY
from wechat.client import WechatClient, load_push_targets

MAX_MSG_LEN = 2000

CN_NEWS_DOMAINS = [
    "sina.com.cn", "finance.sina.com.cn", "eastmoney.com", "caixin.com",
    "163.com", "sohu.com", "caiwennews.com", "xueqiu.com", "cls.cn",
    "stcn.com", "hexun.com", "wallstreetcn.com", "jiemian.com",
    "thepaper.cn", "yicai.com", "36kr.com", "gelonghui.com",
]


def _log(msg: str):
    ts = time.strftime("%H:%M:%S")
    sys.stderr.write(f"[{ts}] [daily-push] {msg}\n")
    sys.stderr.flush()


# ── 行情快照 ──────────────────────────────────────────────

def _format_quote(q: dict) -> str:
    """将单只股票行情格式化为一行摘要。"""
    sign = "+" if q["change_pct"] >= 0 else ""
    currency = q.get("currency", "")
    return (
        f"{q['name_cn']} {q['stock_key']} ({q['market']})\n"
        f"  收盘: {currency}{q['price']:.2f}  "
        f"{sign}{q['change_pct']:.2f}%  "
        f"高: {currency}{q['high']:.2f}  低: {currency}{q['low']:.2f}"
    )


def build_quote_section() -> str:
    """构建行情快照段落。"""
    quotes = fetch_all_watched()
    if not quotes:
        return "━━ 行情快照 ━━\n(行情数据暂不可用)"

    lines = ["━━ 行情快照 ━━"]
    for q in quotes:
        lines.append(_format_quote(q))
    return "\n".join(lines)


# ── 新闻搜索 ──────────────────────────────────────────────

def _parse_pub_date(date_str: str) -> datetime | None:
    """解析 Tavily 返回的 published_date 字符串。"""
    if not date_str:
        return None
    from email.utils import parsedate_to_datetime
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _is_within_24h(item: dict) -> bool:
    """判断新闻是否在最近 24 小时内发布。无日期的默认拒绝。"""
    date_str = item.get("published_date", "")
    if not date_str:
        return False
    pub = _parse_pub_date(date_str)
    if not pub:
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    return pub >= cutoff


def _tavily_search(query: str, max_results: int = 3) -> list[dict]:
    """调用 Tavily 原始 SDK 搜索 24 小时内的中文新闻。"""
    if not TAVILY_API_KEY:
        return []
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=TAVILY_API_KEY)
        response = client.search(
            query=query,
            topic="news",
            days=1,
            max_results=max_results + 8,
            include_domains=CN_NEWS_DOMAINS,
        )
        items = response.get("results", [])
        recent = [it for it in items if _is_within_24h(it)]
        _log(f"  搜索到 {len(items)} 条，24h 内 {len(recent)} 条")
        return recent[:max_results]
    except Exception as e:
        _log(f"Tavily 搜索失败 ({query}): {e}")
    return []


def _format_news_item(idx: int, item: dict) -> str:
    """格式化单条新闻，附带发布时间。"""
    title = item.get("title", "").strip()
    url = item.get("url", "")
    content = item.get("content", "").strip()
    if len(content) > 120:
        content = content[:117] + "..."
    if not title:
        domain = url.split("/")[2] if "/" in url else url
        title = domain
    pub = _parse_pub_date(item.get("published_date", ""))
    time_tag = ""
    if pub:
        local_time = pub + timedelta(hours=8)
        time_tag = f" [{local_time.strftime('%m-%d %H:%M')}]"
    return f"{idx}. {title}{time_tag}\n   {content}\n   {url}"


def build_news_section(name: str, query: str) -> str:
    """构建单个公司的新闻段落。"""
    items = _tavily_search(query, max_results=3)
    lines = [f"━━ {name}资讯 ━━"]
    if not items:
        lines.append("(近24小时内暂无相关资讯)")
    else:
        for i, item in enumerate(items, 1):
            lines.append(_format_news_item(i, item))
    return "\n".join(lines)


def build_industry_section() -> str:
    """构建行业动态段落。"""
    items = _tavily_search("激光雷达 行业动态 自动驾驶 最新消息", max_results=3)
    lines = ["━━ 行业动态 ━━"]
    if not items:
        lines.append("(近24小时内暂无行业动态)")
    else:
        for i, item in enumerate(items, 1):
            lines.append(_format_news_item(i, item))
    return "\n".join(lines)


# ── 组装完整推送 ──────────────────────────────────────────

def build_daily_report() -> str:
    """生成完整的每日激光雷达早报。"""
    today = datetime.now().strftime("%Y-%m-%d")
    header = f"【每日激光雷达早报】{today}"

    sections = [header, ""]

    _log("获取行情数据...")
    sections.append(build_quote_section())
    sections.append("")

    _log("搜索禾赛科技资讯...")
    sections.append(build_news_section("禾赛科技", "禾赛科技 激光雷达 最新消息"))
    sections.append("")

    _log("搜索速腾聚创资讯...")
    sections.append(build_news_section("速腾聚创", "速腾聚创 激光雷达 最新消息"))
    sections.append("")

    _log("搜索行业动态...")
    sections.append(build_industry_section())

    return "\n".join(sections)


# ── 推送到微信 ────────────────────────────────────────────

def push_to_wechat(report: str) -> int:
    """将报告推送给所有已保存的微信用户。返回成功推送的用户数。"""
    targets = load_push_targets()
    if not targets:
        _log("没有推送目标，请先通过微信与 Bot 对话以注册推送。")
        return 0

    client = WechatClient()
    sent = 0

    for user_id, info in targets.items():
        context_token = info.get("context_token")
        if not context_token:
            continue

        short_id = user_id.split("@")[0][:12]
        try:
            # 微信单条消息有长度限制，分段发送
            for i in range(0, len(report), MAX_MSG_LEN):
                chunk = report[i:i + MAX_MSG_LEN]
                client.send_message(user_id, context_token, chunk)
                if i + MAX_MSG_LEN < len(report):
                    time.sleep(0.5)
            sent += 1
            _log(f"推送成功: {short_id}")
        except Exception as e:
            _log(f"推送失败 ({short_id}): {e}")

    return sent


def run_daily_push(dry_run: bool = False) -> str:
    """执行一次每日推送。返回生成的报告内容。"""
    _log("开始生成每日激光雷达早报...")
    report = build_daily_report()
    _log(f"报告生成完毕，长度: {len(report)} 字")

    if dry_run:
        print(report)
        _log("dry-run 模式，不发送微信。")
    else:
        count = push_to_wechat(report)
        _log(f"推送完成，成功 {count} 人。")

    return report


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    run_daily_push(dry_run=dry)
