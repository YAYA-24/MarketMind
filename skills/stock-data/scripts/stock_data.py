"""
A 股行情数据 Skill。

数据源：全部使用新浪财经 API（快速稳定，不易被封）。
- 实时行情：hq.sinajs.cn
- 历史K线：quotes.sina.cn（JSONP 接口）
"""

import re
import requests
import pandas as pd
from langchain_core.tools import tool

from src.sina import SINA_HEADERS, get_sina_prefix, parse_sina_quote, get_sina_kline


@tool
def get_stock_price(symbol: str) -> str:
    """查询单只 A 股的实时行情数据，包括最新价、涨跌幅、成交量、最高价、最低价等。

    Args:
        symbol: 股票代码，6位数字，例如 "600519" 代表贵州茅台，"000001" 代表平安银行
    """
    try:
        sina_symbol = get_sina_prefix(symbol)
        url = f"https://hq.sinajs.cn/list={sina_symbol}"
        r = requests.get(url, headers=SINA_HEADERS, timeout=10)
        r.encoding = "gbk"

        data = parse_sina_quote(r.text)
        if not data:
            return f"未找到股票 {symbol} 的行情数据，请确认代码是否正确。"

        change = data["最新价"] - data["昨收"]
        change_pct = (change / data["昨收"]) * 100 if data["昨收"] != 0 else 0
        volume_hands = data["成交量"] / 100

        return (
            f"股票: {data['名称']} ({symbol})\n"
            f"最新价: {data['最新价']:.2f} 元\n"
            f"涨跌: {change:+.2f} 元 ({change_pct:+.2f}%)\n"
            f"今开: {data['今开']:.2f}\n"
            f"最高: {data['最高']:.2f}\n"
            f"最低: {data['最低']:.2f}\n"
            f"昨收: {data['昨收']:.2f}\n"
            f"成交量: {volume_hands:.0f} 手\n"
            f"成交额: {data['成交额'] / 1e8:.2f} 亿元\n"
            f"数据时间: {data['日期']} {data['时间']}"
        )

    except Exception as e:
        return f"查询股票 {symbol} 行情失败: {str(e)}"


@tool
def get_multi_stock_prices(symbols: str) -> str:
    """同时查询多只 A 股的实时行情，方便对比。

    Args:
        symbols: 多个股票代码，用逗号分隔，例如 "600519,000001,000858"
    """
    try:
        code_list = [s.strip() for s in symbols.split(",")]
        sina_symbols = ",".join(get_sina_prefix(c) for c in code_list)

        url = f"https://hq.sinajs.cn/list={sina_symbols}"
        r = requests.get(url, headers=SINA_HEADERS, timeout=10)
        r.encoding = "gbk"

        lines = ["股票代码  | 名称       | 最新价    | 涨跌幅    | 成交额(亿)", "-" * 65]

        for raw_line in r.text.strip().split(";"):
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            code_match = re.search(r"str_[a-z]{2}(\d{6})", raw_line)
            code = code_match.group(1) if code_match else "??????"
            data = parse_sina_quote(raw_line)
            if not data:
                continue

            change_pct = ((data["最新价"] - data["昨收"]) / data["昨收"] * 100
                          if data["昨收"] != 0 else 0)
            amount_yi = data["成交额"] / 1e8

            lines.append(
                f"{code}    | {data['名称']:<6} | {data['最新价']:>9.2f} | "
                f"{change_pct:>+7.2f}%  | {amount_yi:>8.2f}"
            )

        return "\n".join(lines)

    except Exception as e:
        return f"批量查询失败: {str(e)}"


@tool
def get_stock_history(symbol: str, period: str = "daily", days: int = 30) -> str:
    """查询单只 A 股的历史K线数据。

    Args:
        symbol: 股票代码，6位数字，例如 "600519"
        period: K线周期，可选 "daily"(日线)、"weekly"(周线)
        days: 查询最近多少天的数据，默认30天
    """
    try:
        scale = 1200 if period == "weekly" else 240
        df = get_sina_kline(symbol, datalen=days, scale=scale)

        if df.empty:
            return f"未找到股票 {symbol} 在该时间段内的数据。"

        latest = df.iloc[-1]
        earliest = df.iloc[0]
        price_change = latest["close"] - earliest["close"]
        change_pct = (price_change / earliest["close"]) * 100

        lines = [
            f"股票代码: {symbol}",
            f"查询周期: {period}，最近 {len(df)} 条",
            f"区间涨跌: {price_change:+.2f} 元 ({change_pct:+.2f}%)",
            f"区间最高: {df['high'].max():.2f} 元",
            f"区间最低: {df['low'].min():.2f} 元",
            f"平均成交量: {df['volume'].mean() / 100:.0f} 手",
            "",
            "最近5个交易日:",
        ]

        for _, row in df.tail(5).iterrows():
            vol_hands = row["volume"] / 100
            day_change = (row["close"] - row["open"]) / row["open"] * 100
            lines.append(
                f"  {row['day']} | 开:{row['open']:.2f} 高:{row['high']:.2f} "
                f"低:{row['low']:.2f} 收:{row['close']:.2f} | "
                f"涨跌:{day_change:+.2f}% 成交量:{vol_hands:.0f}手"
            )

        return "\n".join(lines)

    except Exception as e:
        return f"查询股票 {symbol} 历史数据失败: {str(e)}"


ALL_TOOLS = [get_stock_price, get_multi_stock_prices, get_stock_history]
