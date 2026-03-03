"""
联网搜索 Skill（基于 Tavily）。

Tavily 是专为 AI Agent 设计的搜索 API：
- 返回结构化文本（不是原始 HTML），可以直接喂给大模型
- 支持指定搜索领域（如 finance）
- 免费额度：1000 次/月

用法：
  1. 去 https://tavily.com 注册，获取 API Key
  2. 把 Key 填入 .env 文件的 TAVILY_API_KEY
"""

from langchain_core.tools import tool
from src.config.settings import TAVILY_API_KEY


@tool
def search_web(query: str) -> str:
    """联网搜索最新的财经新闻、市场动态、公司公告等实时信息。适用于需要最新数据的场景。

    Args:
        query: 搜索关键词，例如 "贵州茅台 最新消息"、"A股 今日行情分析"、"新能源板块 利好政策"
    """
    if not TAVILY_API_KEY:
        return "Tavily API Key 未配置。请在 .env 文件中设置 TAVILY_API_KEY。"

    try:
        from langchain_tavily import TavilySearch

        search = TavilySearch(
            max_results=5,
            topic="news",
            tavily_api_key=TAVILY_API_KEY,
        )

        results = search.invoke({"query": query})

        if isinstance(results, str):
            return results

        if isinstance(results, list):
            lines = [f"搜索 '{query}' 的结果：\n"]
            for i, item in enumerate(results, 1):
                url = item.get("url", "")
                content = item.get("content", "")
                lines.append(f"【{i}】{url}")
                lines.append(f"    {content[:300]}")
                lines.append("")
            return "\n".join(lines)

        return str(results)

    except Exception as e:
        return f"联网搜索失败: {str(e)}"


@tool
def search_stock_news(stock_name: str) -> str:
    """联网搜索某只股票的最新新闻和分析。比通用搜索更有针对性。

    Args:
        stock_name: 股票名称或代码，例如 "贵州茅台"、"比亚迪"、"宁德时代"
    """
    query = f"{stock_name} 股票 最新消息 分析 A股"
    return search_web.invoke({"query": query})


WEB_SEARCH_TOOLS = [search_web, search_stock_news]
