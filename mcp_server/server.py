"""
A 股分析 MCP Server。

这个文件是一个独立的 MCP 工具服务器。它把我们之前写的 Skill 能力
通过 MCP 协议暴露出去，任何支持 MCP 的客户端都可以调用：
  - Cursor IDE
  - Claude Desktop
  - 其他支持 MCP 的 Agent 框架

启动方式（开发调试）：
  python mcp_server/server.py

MCP 协议通信方式：
  通过 stdin/stdout 的 JSON-RPC 消息（stdio 模式），
  客户端启动本进程后直接通过管道通信，无需 HTTP 端口。
"""

import os
import re
import sys
import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# 加载 .env 配置
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# ── 创建 MCP Server 实例 ──────────────────────────────────
# name 会在客户端显示，帮助用户识别这是哪个工具服务器

mcp = FastMCP("A股分析助手")

# ── 行情数据工具 ──────────────────────────────────────────
# 复用之前 src/skills/stock_data.py 中的新浪财经 API 逻辑

SINA_HEADERS = {"Referer": "https://finance.sina.com.cn"}


def _get_sina_prefix(symbol: str) -> str:
    return f"sh{symbol}" if symbol.startswith("6") else f"sz{symbol}"


def _parse_sina_quote(raw: str) -> dict | None:
    match = re.search(r'"(.*)"', raw)
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
        "成交量": int(fields[8]),
        "成交额": float(fields[9]),
        "日期": fields[30],
        "时间": fields[31],
    }


@mcp.tool()
def get_stock_price(symbol: str) -> str:
    """查询单只 A 股的实时行情数据，包括最新价、涨跌幅、成交量等。

    Args:
        symbol: 股票代码，6位数字，如 "600519" 代表贵州茅台
    """
    try:
        sina_symbol = _get_sina_prefix(symbol)
        r = requests.get(
            f"https://hq.sinajs.cn/list={sina_symbol}",
            headers=SINA_HEADERS, timeout=10,
        )
        r.encoding = "gbk"
        data = _parse_sina_quote(r.text)
        if not data:
            return f"未找到股票 {symbol} 的行情数据。"

        change = data["最新价"] - data["昨收"]
        pct = (change / data["昨收"]) * 100 if data["昨收"] else 0
        vol = data["成交量"] / 100

        return (
            f"股票: {data['名称']} ({symbol})\n"
            f"最新价: {data['最新价']:.2f} 元\n"
            f"涨跌: {change:+.2f} 元 ({pct:+.2f}%)\n"
            f"今开: {data['今开']:.2f} | 最高: {data['最高']:.2f} | 最低: {data['最低']:.2f}\n"
            f"昨收: {data['昨收']:.2f}\n"
            f"成交量: {vol:.0f} 手 | 成交额: {data['成交额']/1e8:.2f} 亿元\n"
            f"数据时间: {data['日期']} {data['时间']}"
        )
    except Exception as e:
        return f"查询失败: {e}"


@mcp.tool()
def get_multi_stock_prices(symbols: str) -> str:
    """同时查询多只 A 股的实时行情，方便对比。

    Args:
        symbols: 多个股票代码，用逗号分隔，如 "600519,000001,000858"
    """
    try:
        codes = [s.strip() for s in symbols.split(",")]
        sina_syms = ",".join(_get_sina_prefix(c) for c in codes)
        r = requests.get(
            f"https://hq.sinajs.cn/list={sina_syms}",
            headers=SINA_HEADERS, timeout=10,
        )
        r.encoding = "gbk"

        lines = ["代码     | 名称     | 最新价    | 涨跌幅    | 成交额(亿)", "-" * 62]
        for raw_line in r.text.strip().split(";"):
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            code_m = re.search(r"str_[a-z]{2}(\d{6})", raw_line)
            code = code_m.group(1) if code_m else "??????"
            data = _parse_sina_quote(raw_line)
            if not data:
                continue
            pct = ((data["最新价"] - data["昨收"]) / data["昨收"] * 100
                   if data["昨收"] else 0)
            lines.append(
                f"{code}   | {data['名称']:<6} | {data['最新价']:>8.2f} | "
                f"{pct:>+7.2f}%  | {data['成交额']/1e8:>7.2f}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"批量查询失败: {e}"


# ── 联网搜索工具 ──────────────────────────────────────────

@mcp.tool()
def search_finance_news(query: str) -> str:
    """联网搜索最新的财经新闻、市场动态、公司公告。

    Args:
        query: 搜索关键词，如 "贵州茅台 最新消息"、"A股 今日行情"
    """
    if not TAVILY_API_KEY:
        return "Tavily API Key 未配置。请在 .env 中设置 TAVILY_API_KEY。"
    try:
        from langchain_tavily import TavilySearch
        search = TavilySearch(
            max_results=5, topic="news", tavily_api_key=TAVILY_API_KEY,
        )
        results = search.invoke({"query": query})

        if isinstance(results, str):
            return results
        if isinstance(results, list):
            lines = [f"搜索 '{query}' 的结果：\n"]
            for i, item in enumerate(results, 1):
                lines.append(f"【{i}】{item.get('url', '')}")
                lines.append(f"    {item.get('content', '')[:300]}")
                lines.append("")
            return "\n".join(lines)
        return str(results)
    except Exception as e:
        return f"搜索失败: {e}"


# ── 技术指标工具 ──────────────────────────────────────────

@mcp.tool()
def get_technical_indicators(symbol: str) -> str:
    """计算某只股票的主要技术指标（MA/MACD/KDJ/RSI/布林带）并给出分析。

    Args:
        symbol: 股票代码，6位数字
    """
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from src.skills.technical import get_technical_indicators as _impl
        return _impl.invoke({"symbol": symbol})
    except Exception as e:
        return f"技术指标计算失败: {e}"


# ── 财务数据工具 ──────────────────────────────────────────

@mcp.tool()
def get_financial_data(symbol: str) -> str:
    """查询上市公司核心财务数据（PE/ROE/营收/资产负债率等）。

    Args:
        symbol: 股票代码，6位数字
    """
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from src.skills.financial import get_financial_data as _impl
        return _impl.invoke({"symbol": symbol})
    except Exception as e:
        return f"财务数据查询失败: {e}"


# ── K线图工具 ─────────────────────────────────────────────

@mcp.tool()
def generate_kline_chart(symbol: str, days: int = 60) -> str:
    """生成 K 线图（蜡烛图），包含日K线、成交量和均线。

    Args:
        symbol: 股票代码
        days: 显示最近多少天，默认60
    """
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from src.skills.kline_chart import generate_kline_chart as _impl
        return _impl.invoke({"symbol": symbol, "days": days})
    except Exception as e:
        return f"K线图生成失败: {e}"


# ── 知识库检索工具 ────────────────────────────────────────

@mcp.tool()
def search_investment_knowledge(query: str) -> str:
    """从投资知识库中检索专业知识（投资书籍、论文中的理论和方法）。

    Args:
        query: 检索问题，如 "什么是安全边际"、"如何分析公司护城河"
    """
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from src.rag.vector_store import search_knowledge, get_db_stats

        stats = get_db_stats()
        if stats["total_documents"] == 0:
            return "投资知识库为空。请先导入书籍: python -m src.rag.ingest path/to/book.pdf"

        results = search_knowledge(query, n_results=5)
        if not results:
            return f"未找到与 '{query}' 相关的内容。"

        lines = [f"知识库检索结果（'{query}'）：\n"]
        for i, r in enumerate(results, 1):
            source = r["metadata"].get("source", "未知")
            distance = r.get("distance")
            rel = f"(相关度: {1-distance:.0%})" if distance is not None else ""
            lines.append(f"【{i}】来源: {source} {rel}")
            lines.append(f"{r['content']}")
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        return f"知识库检索失败: {e}"


# ── 启动 Server ───────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
