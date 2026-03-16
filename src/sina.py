"""
新浪财经 API 公共模块。

统一封装行情、K 线等接口，供 stock-data、technical-analysis、kline-chart、monitor 共用。
"""

import re
import json
import requests
import pandas as pd

SINA_HEADERS = {"Referer": "https://finance.sina.com.cn"}


def get_sina_prefix(symbol: str) -> str:
    """根据股票代码判断交易所前缀：6开头=上海(sh)，其他=深圳(sz)。"""
    return f"sh{symbol}" if symbol.startswith("6") else f"sz{symbol}"


def parse_sina_quote(raw: str) -> dict | None:
    """解析新浪实时行情字符串。

    格式: var hq_str_shXXXXXX="名称,今开,昨收,最新价,最高,最低,买一,卖一,成交量,成交额,...日期,时间,...";

    Returns:
        dict with keys: 名称, 今开, 昨收, 最新价, 最高, 最低, 买一, 卖一, 成交量, 成交额, 日期, 时间
        或 None（解析失败时）
    """
    match = re.search(r'"([^"]*)"', raw)
    if not match or not match.group(1):
        return None

    fields = match.group(1).split(",")
    if len(fields) < 32:
        return None

    return {
        "名称": fields[0],
        "今开": float(fields[1]),
        "昨收": float(fields[2]),
        "最新价": float(fields[3]),
        "最高": float(fields[4]),
        "最低": float(fields[5]),
        "买一": float(fields[6]),
        "卖一": float(fields[7]),
        "成交量": int(fields[8]),
        "成交额": float(fields[9]),
        "日期": fields[30],
        "时间": fields[31],
    }


def get_sina_kline(symbol: str, datalen: int = 60, scale: int = 240) -> pd.DataFrame:
    """从新浪获取历史 K 线数据。

    Args:
        symbol: 6 位股票代码
        datalen: 返回的 K 线条数
        scale: K 线周期（分钟），240=日线，1200=周线

    Returns:
        DataFrame with columns: day, open, high, low, close, volume
    """
    sina_sym = get_sina_prefix(symbol)
    url = "https://quotes.sina.cn/cn/api/jsonp_v2.php/var/CN_MarketDataService.getKLineData"
    params = {"symbol": sina_sym, "scale": str(scale), "ma": "no", "datalen": str(datalen)}
    r = requests.get(url, params=params, headers=SINA_HEADERS, timeout=15)
    r.encoding = "utf-8"

    match = re.search(r"\((\[.*\])\)", r.text)
    if not match:
        return pd.DataFrame()

    rows = json.loads(match.group(1))
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].astype(float)
    df["volume"] = df["volume"].astype(int)
    return df


def fetch_realtime_quote(symbol: str) -> dict | None:
    """从新浪获取单只股票实时行情（简化格式，供 monitor 等使用）。

    Returns:
        dict with: symbol, name, price, change_pct, volume, amount, time
        或 None
    """
    try:
        sina_sym = get_sina_prefix(symbol)
        r = requests.get(
            f"https://hq.sinajs.cn/list={sina_sym}",
            headers=SINA_HEADERS,
            timeout=10,
        )
        r.encoding = "gbk"
        data = parse_sina_quote(r.text)
        if not data:
            return None

        change_pct = (
            (data["最新价"] - data["昨收"]) / data["昨收"] * 100
            if data["昨收"] != 0
            else 0
        )
        return {
            "symbol": symbol,
            "name": data["名称"],
            "price": data["最新价"],
            "change_pct": round(change_pct, 2),
            "volume": data["成交量"],
            "amount": data["成交额"],
            "time": f"{data['日期']} {data['时间']}",
        }
    except Exception:
        return None
