"""
港美股行情数据模块。

数据源：新浪财经 API（与 A 股同一 API，不同前缀和解析格式）。
- 美股：hq.sinajs.cn/list=gb_{ticker}
- 港股：hq.sinajs.cn/list=hk{code}
"""

import re
import requests

SINA_HEADERS = {"Referer": "https://finance.sina.com.cn"}

# ── 预定义关注的港美股 ──────────────────────────────────
WATCHED_STOCKS = {
    "HSAI": {
        "sina_symbol": "gb_hsai",
        "name_cn": "禾赛科技",
        "market": "NASDAQ",
        "currency": "$",
    },
    "02498": {
        "sina_symbol": "hk02498",
        "name_cn": "速腾聚创",
        "market": "HKEX",
        "currency": "HK$",
    },
}


def _fetch_raw(sina_symbol: str) -> str | None:
    """调用 Sina API 获取原始行情字符串。"""
    url = f"https://hq.sinajs.cn/list={sina_symbol}"
    try:
        r = requests.get(url, headers=SINA_HEADERS, timeout=10)
        r.encoding = "gbk"
        match = re.search(r'"([^"]*)"', r.text)
        if match and match.group(1):
            return match.group(1)
    except Exception:
        pass
    return None


def parse_us_quote(raw: str) -> dict | None:
    """解析美股行情字符串。

    格式: 名称,最新价,涨跌幅%,时间,涨跌额,今开,最高,最低,52周高,52周低,成交量,...,昨收(field26)
    """
    fields = raw.split(",")
    if len(fields) < 27:
        return None
    try:
        return {
            "name": fields[0],
            "price": float(fields[1]),
            "change_pct": float(fields[2]),
            "change": float(fields[4]),
            "open": float(fields[5]),
            "high": float(fields[6]),
            "low": float(fields[7]),
            "high_52w": float(fields[8]),
            "low_52w": float(fields[9]),
            "volume": int(fields[10]),
            "prev_close": float(fields[26]),
            "datetime": fields[3],
        }
    except (ValueError, IndexError):
        return None


def parse_hk_quote(raw: str) -> dict | None:
    """解析港股行情字符串。

    格式: 英文名,中文名,今开,昨收,最高,最低,最新价,涨跌额,涨跌幅%,买入,卖出,成交额,成交量,...,52周高,52周低,日期,时间
    """
    fields = raw.split(",")
    if len(fields) < 18:
        return None
    try:
        return {
            "name": fields[1] or fields[0],
            "price": float(fields[6]),
            "change_pct": float(fields[8]),
            "change": float(fields[7]),
            "open": float(fields[2]),
            "high": float(fields[4]),
            "low": float(fields[5]),
            "prev_close": float(fields[3]),
            "turnover": float(fields[11]),
            "volume": int(fields[12]),
            "high_52w": float(fields[15]) if fields[15] else 0,
            "low_52w": float(fields[16]) if fields[16] else 0,
            "datetime": f"{fields[17]} {fields[18]}".strip(),
        }
    except (ValueError, IndexError):
        return None


def fetch_global_quote(stock_key: str) -> dict | None:
    """获取一只港/美股的行情快照。

    Args:
        stock_key: WATCHED_STOCKS 中的 key，如 "HSAI" 或 "02498"

    Returns:
        统一格式的 dict，包含 name, price, change_pct, change, open, high, low,
        prev_close, volume, datetime, market, currency 等字段，或 None。
    """
    meta = WATCHED_STOCKS.get(stock_key)
    if not meta:
        return None

    raw = _fetch_raw(meta["sina_symbol"])
    if not raw:
        return None

    is_us = meta["sina_symbol"].startswith("gb_")
    parsed = parse_us_quote(raw) if is_us else parse_hk_quote(raw)
    if not parsed:
        return None

    parsed["stock_key"] = stock_key
    parsed["market"] = meta["market"]
    parsed["currency"] = meta["currency"]
    parsed["name_cn"] = meta["name_cn"]
    return parsed


def fetch_all_watched() -> list[dict]:
    """获取所有关注港美股的行情。"""
    results = []
    for key in WATCHED_STOCKS:
        data = fetch_global_quote(key)
        if data:
            results.append(data)
    return results
