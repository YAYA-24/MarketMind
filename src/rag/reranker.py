"""
RAG Rerank 模块。

Cross-Encoder 对 (query, doc) 对进行相关性打分，显著提升 Top-K 精度。
流程：Top 20 docs → Rerank → Top 5 → Generate
"""

RERANKER_MODEL = "BAAI/bge-reranker-base"
MAX_PAIR_LENGTH = 512  # BGE-reranker 最大序列长度


def _get_reranker():
    """懒加载 Cross-Encoder，避免启动时加载。"""
    try:
        from sentence_transformers import CrossEncoder

        return CrossEncoder(RERANKER_MODEL)
    except ImportError:
        raise ImportError("Rerank 需安装: pip install sentence-transformers")


_reranker = None


def get_reranker():
    global _reranker
    if _reranker is None:
        _reranker = _get_reranker()
    return _reranker


def rerank(
    query: str,
    documents: list[dict],
    top_k: int = 5,
    content_key: str = "content",
) -> list[dict]:
    """
    对检索结果进行 Cross-Encoder 重排序。

    Args:
        query: 检索问题
        documents: 文档列表，每项为 dict，需含 content_key 字段（用于打分）
        top_k: 返回数量
        content_key: 文档内容字段名（默认 "content"，即 parent_content）

    Returns:
        按相关性排序的文档列表。若 Cross-Encoder 不可用，返回原顺序前 top_k。
    """
    if not documents:
        return []

    try:
        model = get_reranker()
    except ImportError:
        return documents[:top_k]

    pairs = [(query, d.get(content_key, "")[:2000]) for d in documents]
    scores = model.predict(pairs)

    scored = list(zip(documents, scores))
    scored.sort(key=lambda x: -x[1])
    return [d for d, _ in scored[:top_k]]
