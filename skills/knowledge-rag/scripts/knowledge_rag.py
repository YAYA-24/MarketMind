"""
投资知识库检索 Skill。

知识库中存储的是投资书籍、学术论文、策略研报等长期不变的专业知识，
例如：价值投资理论、技术分析方法论、量化策略、风险管理框架等。

与联网搜索的分工：
- 联网搜索 → 获取最新新闻、实时动态
- 知识库检索 → 获取专业理论、分析框架、历史经验
"""

from langchain_core.tools import tool

from src.rag.context_builder import build_context
from src.rag.vector_store import search_knowledge, get_db_stats


@tool
def search_investment_knowledge(query: str) -> str:
    """从投资知识库中检索专业知识，包括投资理论、分析方法、策略框架等。知识库内容来自投资书籍、学术论文、研究报告。

    适用场景：
    - 需要理论支撑时，如"什么是安全边际"、"DCF估值方法"
    - 需要分析框架时，如"如何分析一家公司的护城河"
    - 需要策略参考时，如"均值回归策略原理"

    Args:
        query: 检索问题，例如 "价值投资的核心原则"、"技术分析中的支撑位和阻力位"
    """
    try:
        stats = get_db_stats()
        if stats["total_documents"] == 0:
            return ("投资知识库为空。请先导入书籍或论文：\n"
                    "  python -m src.rag.ingest path/to/your-book.pdf\n"
                    "支持 PDF、TXT、MD 格式。")

        results = search_knowledge(query, n_results=5)
        if not results:
            return f"未找到与「{query}」相关的内容。"

        return build_context(
            results,
            query=query,
            token_budget=4000,
            dedupe=True,
            include_header=True,
        )

    except Exception as e:
        return f"知识库检索失败: {str(e)}"


@tool
def get_knowledge_db_info() -> str:
    """查看投资知识库的状态，包括已导入的文档数量。"""
    try:
        stats = get_db_stats()
        return (
            f"投资知识库状态:\n"
            f"  文档片段总数: {stats['total_documents']}\n"
            f"  存储路径: {stats['db_path']}"
        )
    except Exception as e:
        return f"获取知识库状态失败: {str(e)}"


KNOWLEDGE_RAG_TOOLS = [search_investment_knowledge, get_knowledge_db_info]
