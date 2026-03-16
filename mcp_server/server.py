"""
A 股分析 MCP Server。

通过 MCP 协议暴露 Skill 能力，供 Cursor IDE、Claude Desktop 等客户端调用。
所有工具实现复用 src.skills，无重复代码。

启动方式（开发调试）：
  python mcp_server/server.py

MCP 协议通信方式：
  通过 stdin/stdout 的 JSON-RPC 消息（stdio 模式），
  客户端启动本进程后直接通过管道通信，无需 HTTP 端口。
"""

import os
import sys

# 确保项目根目录在 sys.path 中，便于导入 src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# 加载 .env 配置
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

mcp = FastMCP("A股分析助手")


# ── 行情数据工具 ──────────────────────────────────────────
# 复用 src.skills.stock_data

@mcp.tool()
def get_stock_price(symbol: str) -> str:
    """查询单只 A 股的实时行情数据，包括最新价、涨跌幅、成交量等。

    Args:
        symbol: 股票代码，6位数字，如 "600519" 代表贵州茅台
    """
    try:
        from src.skills.stock_data import get_stock_price as _impl
        return _impl.invoke({"symbol": symbol})
    except Exception as e:
        return f"查询失败: {e}"


@mcp.tool()
def get_multi_stock_prices(symbols: str) -> str:
    """同时查询多只 A 股的实时行情，方便对比。

    Args:
        symbols: 多个股票代码，用逗号分隔，如 "600519,000001,000858"
    """
    try:
        from src.skills.stock_data import get_multi_stock_prices as _impl
        return _impl.invoke({"symbols": symbols})
    except Exception as e:
        return f"批量查询失败: {e}"


@mcp.tool()
def get_stock_history(symbol: str, period: str = "daily", days: int = 30) -> str:
    """查询单只 A 股的历史K线数据。

    Args:
        symbol: 股票代码，6位数字，如 "600519"
        period: K线周期，可选 "daily"(日线)、"weekly"(周线)
        days: 查询最近多少天的数据，默认30天
    """
    try:
        from src.skills.stock_data import get_stock_history as _impl
        return _impl.invoke({"symbol": symbol, "period": period, "days": days})
    except Exception as e:
        return f"查询历史数据失败: {e}"


# ── 联网搜索工具 ──────────────────────────────────────────
# 复用 src.skills.web_search

@mcp.tool()
def search_finance_news(query: str) -> str:
    """联网搜索最新的财经新闻、市场动态、公司公告。

    Args:
        query: 搜索关键词，如 "贵州茅台 最新消息"、"A股 今日行情"
    """
    try:
        from src.skills.web_search import search_web as _impl
        return _impl.invoke({"query": query})
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
        from src.skills.kline_chart import generate_kline_chart as _impl
        return _impl.invoke({"symbol": symbol, "days": days})
    except Exception as e:
        return f"K线图生成失败: {e}"


# ── 知识库检索工具 ────────────────────────────────────────
# 复用 src.skills.news_rag

@mcp.tool()
def search_investment_knowledge(query: str) -> str:
    """从投资知识库中检索专业知识（投资书籍、论文中的理论和方法）。

    Args:
        query: 检索问题，如 "什么是安全边际"、"如何分析公司护城河"
    """
    try:
        from src.skills.news_rag import search_investment_knowledge as _impl
        return _impl.invoke({"query": query})
    except Exception as e:
        return f"知识库检索失败: {e}"


# ── 启动 Server ───────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
