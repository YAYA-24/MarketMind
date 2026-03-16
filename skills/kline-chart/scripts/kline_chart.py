"""
K 线图生成 Skill。

使用 mplfinance 生成专业的 K 线图并保存为图片。
数据源：新浪财经历史 K 线 API。
"""

import requests
import pandas as pd
import matplotlib
matplotlib.use('Agg')
from langchain_core.tools import tool

from src.config.settings import CHART_DIR
from src.sina import SINA_HEADERS, get_sina_prefix, parse_sina_quote, get_sina_kline


def _get_stock_name(symbol: str) -> str:
    """获取股票名称用于图表标题。"""
    try:
        sina_sym = get_sina_prefix(symbol)
        r = requests.get(
            f"https://hq.sinajs.cn/list={sina_sym}",
            headers=SINA_HEADERS, timeout=5,
        )
        r.encoding = "gbk"
        data = parse_sina_quote(r.text)
        if data:
            return data["名称"]
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
        import mplfinance as mpf

        df = get_sina_kline(symbol, datalen=days, scale=240)
        if df.empty:
            return f"未获取到股票 {symbol} 的历史数据。"

        df = df.rename(columns={
            "day": "Date", "open": "Open", "close": "Close",
            "high": "High", "low": "Low", "volume": "Volume",
        })
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date").sort_index()

        stock_name = _get_stock_name(symbol)

        CHART_DIR.mkdir(parents=True, exist_ok=True)
        filepath = CHART_DIR / f"{symbol}_kline.png"

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
            savefig=dict(fname=str(filepath), dpi=150, bbox_inches="tight"),
        )

        abs_path = str(filepath.resolve())
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
