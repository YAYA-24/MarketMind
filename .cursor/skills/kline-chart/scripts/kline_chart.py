"""
K 线图生成 Skill。

使用 mplfinance 生成专业的 K 线图并保存为图片。
数据源：新浪财经历史 K 线 API。
"""

import os
import re
import requests
import pandas as pd
import matplotlib
matplotlib.use('Agg')
from langchain_core.tools import tool

CHART_DIR = os.path.abspath(os.path.join(os.getcwd(), 'data', 'charts'))
SINA_HEADERS = {"Referer": "https://finance.sina.com.cn"}


def _get_sina_prefix(symbol: str) -> str:
    return f"sh{symbol}" if symbol.startswith("6") else f"sz{symbol}"


def _get_stock_name(symbol: str) -> str:
    try:
        sina_sym = _get_sina_prefix(symbol)
        r = requests.get(
            f"https://hq.sinajs.cn/list={sina_sym}",
            headers=SINA_HEADERS, timeout=5,
        )
        r.encoding = "gbk"
        m = re.search(r'"([^"]*)"', r.text)
        if m and m.group(1):
            return m.group(1).split(",")[0]
    except Exception:
        pass
    return symbol


@tool
def generate_kline_chart(symbol: str, days: int = 60) -> str:
    """生成某只股票的 K 线图（蜡烛图），包含日K线、成交量和移动平均线，保存为图片文件。

    Args:
        symbol: 股票代码，6位数字，例如 "600519"
        days: 显示最近多少天的K线，默认60天
    """
    try:
        import json
        import mplfinance as mpf

        sina_sym = _get_sina_prefix(symbol)
        url = "https://quotes.sina.cn/cn/api/jsonp_v2.php/var/CN_MarketDataService.getKLineData"
        params = {"symbol": sina_sym, "scale": "240", "ma": "no", "datalen": str(days)}
        r = requests.get(url, params=params, headers=SINA_HEADERS, timeout=15)

        match = re.search(r'\((\[.*\])\)', r.text)
        if not match:
            return f"未获取到股票 {symbol} 的历史数据。"

        rows = json.loads(match.group(1))
        if not rows:
            return f"未获取到股票 {symbol} 的数据。"

        df = pd.DataFrame(rows)
        df = df.rename(columns={
            "day": "Date", "open": "Open", "close": "Close",
            "high": "High", "low": "Low", "volume": "Volume",
        })
        for col in ["Open", "High", "Low", "Close"]:
            df[col] = df[col].astype(float)
        df["Volume"] = df["Volume"].astype(int)
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date").sort_index()

        stock_name = _get_stock_name(symbol)

        os.makedirs(CHART_DIR, exist_ok=True)
        filepath = os.path.join(CHART_DIR, f"{symbol}_kline.png")

        style = mpf.make_mpf_style(
            base_mpf_style="charles",
            marketcolors=mpf.make_marketcolors(
                up="red", down="green",
                edge="inherit", wick="inherit",
                volume="in",
            ),
        )

        mpf.plot(
            df, type="candle", style=style,
            title=f"\n{stock_name} ({symbol}) K线图",
            ylabel="价格 (元)",
            ylabel_lower="成交量",
            volume=True,
            mav=(5, 10, 20),
            figsize=(14, 8),
            savefig=dict(fname=filepath, dpi=150, bbox_inches="tight"),
        )

        abs_path = os.path.abspath(filepath)
        return (
            f"K线图已生成！\n"
            f"股票: {stock_name} ({symbol})\n"
            f"周期: 最近 {days} 天日K线\n"
            f"包含: K线 + 成交量 + MA5/MA10/MA20 均线\n"
            f"文件路径: {abs_path}"
        )

    except Exception as e:
        return f"生成K线图失败: {e}"


KLINE_TOOLS = [generate_kline_chart]
