"""
技术指标分析 Skill。

基于新浪历史 K 线数据计算常用技术指标：
- MA（移动平均线）
- MACD（异同移动平均线）
- KDJ（随机指标）
- RSI（相对强弱指标）
- 布林带（Bollinger Bands）

数据源：新浪财经历史 K 线 API。
"""

import re
import json
import requests
import pandas as pd
import pandas_ta as ta
from langchain_core.tools import tool

SINA_HEADERS = {"Referer": "https://finance.sina.com.cn"}


def _get_sina_prefix(symbol: str) -> str:
    return f"sh{symbol}" if symbol.startswith("6") else f"sz{symbol}"


def _get_hist_df(symbol: str, datalen: int = 120) -> pd.DataFrame:
    """从新浪获取历史 K 线并转为计算友好的 DataFrame。"""
    sina_sym = _get_sina_prefix(symbol)
    url = "https://quotes.sina.cn/cn/api/jsonp_v2.php/var/CN_MarketDataService.getKLineData"
    params = {"symbol": sina_sym, "scale": "240", "ma": "no", "datalen": str(datalen)}
    r = requests.get(url, params=params, headers=SINA_HEADERS, timeout=15)

    match = re.search(r'\((\[.*\])\)', r.text)
    if not match:
        return pd.DataFrame()

    rows = json.loads(match.group(1))
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df = df.rename(columns={"day": "date"})
    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].astype(float)
    df["volume"] = df["volume"].astype(int)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    return df


@tool
def get_technical_indicators(symbol: str) -> str:
    """计算某只股票的主要技术指标，包括 MA、MACD、KDJ、RSI、布林带，并给出技术面分析。

    Args:
        symbol: 股票代码，6位数字，例如 "600519"
    """
    try:
        df = _get_hist_df(symbol, datalen=120)
        if df.empty or len(df) < 30:
            return f"股票 {symbol} 的历史数据不足，无法计算技术指标。"

        close = df["close"]
        high = df["high"]
        low = df["low"]
        latest = close.iloc[-1]

        ma5 = close.rolling(5).mean().iloc[-1]
        ma10 = close.rolling(10).mean().iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1]
        ma60 = close.rolling(60).mean().iloc[-1] if len(df) >= 60 else None

        macd = ta.macd(close)
        macd_val = macd.iloc[-1, 0]
        signal_val = macd.iloc[-1, 1]
        hist_val = macd.iloc[-1, 2]

        kdj = ta.stoch(high, low, close)
        k_val = kdj.iloc[-1, 0]
        d_val = kdj.iloc[-1, 1]
        j_val = 3 * k_val - 2 * d_val

        rsi6 = ta.rsi(close, length=6).iloc[-1]
        rsi12 = ta.rsi(close, length=12).iloc[-1]
        rsi24 = ta.rsi(close, length=24).iloc[-1]

        bbands = ta.bbands(close, length=20)
        bb_upper = bbands.iloc[-1, 0]
        bb_mid = bbands.iloc[-1, 1]
        bb_lower = bbands.iloc[-1, 2]

        signals = []
        if ma5 > ma10 > ma20:
            signals.append("MA 多头排列（短期均线在上），趋势偏多")
        elif ma5 < ma10 < ma20:
            signals.append("MA 空头排列（短期均线在下），趋势偏空")
        else:
            signals.append("MA 均线交织，趋势不明朗")

        if hist_val > 0 and macd_val > signal_val:
            signals.append("MACD 金叉且柱状线为正，做多信号")
        elif hist_val < 0 and macd_val < signal_val:
            signals.append("MACD 死叉且柱状线为负，做空信号")

        if k_val > 80 and d_val > 80:
            signals.append("KDJ 超买区（K/D > 80），注意回调风险")
        elif k_val < 20 and d_val < 20:
            signals.append("KDJ 超卖区（K/D < 20），可能存在反弹机会")

        if rsi6 > 80:
            signals.append("RSI6 超买（> 80），短期过热")
        elif rsi6 < 20:
            signals.append("RSI6 超卖（< 20），短期超跌")

        if latest > bb_upper:
            signals.append("价格突破布林带上轨，可能超买")
        elif latest < bb_lower:
            signals.append("价格跌破布林带下轨，可能超卖")

        ma60_line = f"  MA60:  {ma60:.2f}\n" if ma60 else ""
        lines = [
            f"股票 {symbol} 技术指标分析（{df.index[-1].strftime('%Y-%m-%d')}）",
            f"当前价格: {latest:.2f}",
            "",
            "【移动平均线 MA】",
            f"  MA5:   {ma5:.2f}",
            f"  MA10:  {ma10:.2f}",
            f"  MA20:  {ma20:.2f}",
            ma60_line +
            "",
            "【MACD】",
            f"  DIF:  {macd_val:.4f}",
            f"  DEA:  {signal_val:.4f}",
            f"  柱状:  {hist_val:.4f}",
            "",
            "【KDJ】",
            f"  K: {k_val:.2f}  D: {d_val:.2f}  J: {j_val:.2f}",
            "",
            "【RSI】",
            f"  RSI6:  {rsi6:.2f}  RSI12: {rsi12:.2f}  RSI24: {rsi24:.2f}",
            "",
            "【布林带】",
            f"  上轨: {bb_upper:.2f}  中轨: {bb_mid:.2f}  下轨: {bb_lower:.2f}",
            "",
            "【综合信号】",
        ]
        for s in signals:
            lines.append(f"  • {s}")

        return "\n".join(lines)

    except Exception as e:
        return f"计算技术指标失败: {e}"


TECHNICAL_TOOLS = [get_technical_indicators]
