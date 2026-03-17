"""
RAG Embedding 模块。

- 金融友好模型：BGE 中文（BAAI/bge-small-zh-v1.5）
- Query Expansion：LLM 扩写同义版本 → 多向量检索 → RRF 融合
"""

import os

# 模型配置
BGE_MODEL = "BAAI/bge-small-zh-v1.5"
DEFAULT_MODEL = "all-MiniLM-L6-v2"  # ChromaDB 默认，384 维


def _get_embedding_model() -> str:
    """从环境变量读取，默认 BGE 中文"""
    return os.getenv("EMBEDDING_MODEL", "bge").lower()


def get_embedding_function():
    """
    获取 ChromaDB 兼容的 embedding 函数。

    环境变量 EMBEDDING_MODEL:
      - bge: BAAI/bge-small-zh-v1.5（中文优化，512 维）
      - default: ChromaDB 默认 all-MiniLM-L6-v2（英文向，384 维）

    切换模型后需重新导入知识库（向量维度不同）。
    """
    model_key = _get_embedding_model()
    if model_key == "default":
        return None  # ChromaDB 使用内置默认

    try:
        from chromadb.utils import embedding_functions

        return embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=BGE_MODEL,
            normalize_embeddings=True,
        )
    except ImportError:
        raise ImportError(
            "使用 BGE 需安装: pip install sentence-transformers"
        )


# ============ Query Expansion ============

# 金融术语简单同义扩展（无需 LLM）
FINANCIAL_SYNONYMS: dict[str, list[str]] = {
    "安全边际": ["margin of safety", "安全边际", "价值投资 安全边际"],
    "护城河": ["护城河", "竞争优势", "moat"],
    "估值": ["估值", "内在价值", "valuation"],
    "DCF": ["DCF", "现金流折现", "贴现现金流"],
    "PE": ["市盈率", "PE", "估值"],
    "ROE": ["净资产收益率", "ROE", "盈利能力"],
    "技术分析": ["技术分析", "K线", "均线", "趋势"],
    "价值投资": ["价值投资", "格雷厄姆", "巴菲特"],
    "基本面": ["基本面", "财务分析", "公司分析"],
}


def _simple_query_expand(query: str, max_extra: int = 2) -> list[str]:
    """
    简单同义扩展：若 query 包含已知金融术语，追加同义表述。
    返回 [原 query, 扩展1, 扩展2, ...]，最多 max_extra 个额外 query。
    """
    queries = [query]
    for term, synonyms in FINANCIAL_SYNONYMS.items():
        if term in query:
            for s in synonyms:
                if s != query and s not in queries:
                    queries.append(s)
                    if len(queries) > max_extra + 1:
                        break
            break  # 只扩展第一个匹配的术语
    return queries[: max_extra + 1]


def _llm_query_expand(query: str, n: int = 3) -> list[str]:
    """
    LLM 扩写：生成 n 个语义相近的检索 query。
    用于多向量检索，提升召回。
    """
    try:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
            openai_api_base=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        )
        prompt = f"""你是一个投资知识库检索助手。用户的问题如下，请生成 {n} 个语义相近、可用于向量检索的改写版本。
要求：保持核心概念，可换用同义词、补充专业术语、拆分为子问题。每行一个，不要编号。

用户问题：{query}

改写（每行一个）："""
        resp = llm.invoke(prompt)
        text = resp.content if hasattr(resp, "content") else str(resp)
        lines = [q.strip() for q in text.strip().split("\n") if q.strip()]
        # 去重，保留原 query
        seen = {query}
        expanded = [query]
        for line in lines:
            if line not in seen and len(expanded) < n + 1:
                seen.add(line)
                expanded.append(line)
        return expanded[: n + 1]
    except Exception:
        return [query]


def expand_query(
    query: str,
    method: str = "simple",
    max_queries: int = 3,
) -> list[str]:
    """
    查询扩展入口。

    Args:
        query: 原始问题
        method: "simple" 规则同义 | "llm" LLM 扩写
        max_queries: 最多生成的 query 数量（含原 query）

    Returns:
        扩展后的 query 列表
    """
    if method == "llm" and os.getenv("DEEPSEEK_API_KEY"):
        return _llm_query_expand(query, n=max_queries - 1)
    return _simple_query_expand(query, max_extra=max_queries - 1)


def reciprocal_rank_fusion(
    ranked_lists: list[list[tuple[str, float]]],
    k: int = 60,
) -> list[tuple[str, float]]:
    """
    RRF 融合多路检索结果。

    Args:
        ranked_lists: 每路检索的 [(doc_id, distance), ...]
        k: RRF 常数，通常 60

    Returns:
        按 RRF 分数排序的 [(doc_id, score), ...]，score 越大越相关
    """
    scores: dict[str, float] = {}
    for rank_list in ranked_lists:
        for rank, (doc_id, _) in enumerate(rank_list):
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank + 1)

    sorted_items = sorted(scores.items(), key=lambda x: -x[1])
    return sorted_items
