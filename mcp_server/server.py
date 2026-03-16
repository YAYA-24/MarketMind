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


def _invoke_skill(module: str, func: str, args: dict, error_msg: str) -> str:
    """统一调用 src.skills 中的工具。"""
    try:
        mod = __import__(f"src.skills.{module}", fromlist=[func])
        impl = getattr(mod, func)
        return impl.invoke(args)
    except Exception as e:
        return f"{error_msg}: {e}"


# ── 行情数据工具 ──────────────────────────────────────────

@mcp.tool()
def get_stock_price(symbol: str) -> str:
    """查询单只 A 股的实时行情数据，包括最新价、涨跌幅、成交量等。

    Args:
        symbol: 股票代码，6位数字，如 "600519" 代表贵州茅台
    """
    return _invoke_skill("stock_data", "get_stock_price", {"symbol": symbol}, "查询失败")


@mcp.tool()
def get_multi_stock_prices(symbols: str) -> str:
    """同时查询多只 A 股的实时行情，方便对比。

    Args:
        symbols: 多个股票代码，用逗号分隔，如 "600519,000001,000858"
    """
    return _invoke_skill("stock_data", "get_multi_stock_prices", {"symbols": symbols}, "批量查询失败")


@mcp.tool()
def get_stock_history(symbol: str, period: str = "daily", days: int = 30) -> str:
    """查询单只 A 股的历史K线数据。

    Args:
        symbol: 股票代码，6位数字，如 "600519"
        period: K线周期，可选 "daily"(日线)、"weekly"(周线)
        days: 查询最近多少天的数据，默认30天
    """
    return _invoke_skill("stock_data", "get_stock_history", {"symbol": symbol, "period": period, "days": days}, "查询历史数据失败")


# ── 联网搜索工具 ──────────────────────────────────────────

@mcp.tool()
def search_web(query: str) -> str:
    """联网搜索最新的财经新闻、市场动态、公司公告。

    Args:
        query: 搜索关键词，如 "贵州茅台 最新消息"、"A股 今日行情"
    """
    return _invoke_skill("web_search", "search_web", {"query": query}, "搜索失败")


@mcp.tool()
def search_stock_news(stock_name: str) -> str:
    """联网搜索某只股票的最新新闻和分析。

    Args:
        stock_name: 股票名称或代码，如 "贵州茅台"、"比亚迪"
    """
    return _invoke_skill("web_search", "search_stock_news", {"stock_name": stock_name}, "搜索失败")


# ── 技术指标工具 ──────────────────────────────────────────

@mcp.tool()
def get_technical_indicators(symbol: str) -> str:
    """计算某只股票的主要技术指标（MA/MACD/KDJ/RSI/布林带）并给出分析。

    Args:
        symbol: 股票代码，6位数字
    """
    return _invoke_skill("technical", "get_technical_indicators", {"symbol": symbol}, "技术指标计算失败")


# ── 财务数据工具 ──────────────────────────────────────────

@mcp.tool()
def get_financial_data(symbol: str) -> str:
    """查询上市公司核心财务数据（PE/ROE/营收/资产负债率等）。

    Args:
        symbol: 股票代码，6位数字
    """
    return _invoke_skill("financial", "get_financial_data", {"symbol": symbol}, "财务数据查询失败")


# ── K线图工具 ─────────────────────────────────────────────

@mcp.tool()
def generate_kline_chart(symbol: str, days: int = 60) -> str:
    """生成 K 线图（蜡烛图），包含日K线、成交量和均线。

    Args:
        symbol: 股票代码
        days: 显示最近多少天，默认60
    """
    return _invoke_skill("kline_chart", "generate_kline_chart", {"symbol": symbol, "days": days}, "K线图生成失败")


# ── 知识库检索工具 ────────────────────────────────────────

@mcp.tool()
def search_investment_knowledge(query: str) -> str:
    """从投资知识库中检索专业知识（投资书籍、论文中的理论和方法）。

    Args:
        query: 检索问题，如 "什么是安全边际"、"如何分析公司护城河"
    """
    return _invoke_skill("knowledge_rag", "search_investment_knowledge", {"query": query}, "知识库检索失败")


@mcp.tool()
def get_knowledge_db_info() -> str:
    """查看投资知识库的状态，包括已导入的文档数量。"""
    return _invoke_skill("knowledge_rag", "get_knowledge_db_info", {}, "获取知识库状态失败")


# ── 监控管理工具 ──────────────────────────────────────────

@mcp.tool()
def add_stock_monitor(symbol: str, condition: str, threshold: float, description: str = "") -> str:
    """添加股票监控规则，当条件满足时提醒用户。

    Args:
        symbol: 股票代码，6位数字
        condition: 条件类型，如 price_above/price_below/change_pct_above/change_pct_below
        threshold: 阈值，如 90 表示 90 元或 90%
        description: 可选描述
    """
    return _invoke_skill("monitor_skill", "add_stock_monitor", {"symbol": symbol, "condition": condition, "threshold": threshold, "description": description}, "添加监控失败")


@mcp.tool()
def list_stock_monitors() -> str:
    """查看当前所有股票监控规则。"""
    return _invoke_skill("monitor_skill", "list_stock_monitors", {}, "获取监控列表失败")


@mcp.tool()
def remove_stock_monitor(rule_id: int) -> str:
    """删除指定的股票监控规则。

    Args:
        rule_id: 规则 ID，可通过 list_stock_monitors 查看
    """
    return _invoke_skill("monitor_skill", "remove_stock_monitor", {"rule_id": rule_id}, "删除监控失败")


# ── 启动 Server ───────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
