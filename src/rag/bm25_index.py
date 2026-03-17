"""
BM25 关键词检索模块。

金融领域对「ROE」「净利润同比」「现金流」等关键词敏感，BM25 与向量检索互补。
"""

from typing import Callable

# 金融领域关键词，加入 jieba 词典确保不被拆分
FINANCIAL_TERMS = [
    "ROE", "PE", "PB", "EPS", "DCF", "EV", "EBITDA",
    "净利润同比", "营收同比", "毛利率", "净利率", "资产负债率",
    "现金流", "经营现金流", "自由现金流", "现金流折现",
    "安全边际", "护城河", "内在价值", "估值",
    "技术分析", "均线", "MACD", "KDJ", "RSI", "布林带",
    "价值投资", "成长股", "周期股",
]


_jieba_initialized = False


def _tokenize(text: str) -> list[str]:
    """中文 + 英文混合分词，金融术语保持完整。"""
    import jieba

    global _jieba_initialized
    if not _jieba_initialized:
        for term in FINANCIAL_TERMS:
            jieba.add_word(term, freq=1000)
        _jieba_initialized = True

    tokens = jieba.lcut(text)
    return [t.strip() for t in tokens if t.strip() and len(t.strip()) > 1]


class BM25Index:
    """BM25 索引，支持 top_k 检索。"""

    def __init__(
        self,
        ids: list[str],
        bm25: object,  # BM25Okapi from rank_bm25
        tokenize_fn: Callable[[str], list[str]],
    ):
        self.ids = ids
        self.bm25 = bm25
        self._tokenize = tokenize_fn

    def search(self, query: str, top_k: int = 50) -> list[tuple[str, float]]:
        """
        检索与 query 最相关的文档。

        Returns:
            [(doc_id, bm25_score), ...]，按分数降序
        """
        import numpy as np

        tokenized_query = self._tokenize(query)
        if not tokenized_query:
            return []

        scores = self.bm25.get_scores(tokenized_query)
        top_indices = np.argsort(scores)[::-1][:top_k]

        return [(self.ids[i], float(scores[i])) for i in top_indices if scores[i] > 0]


def build_bm25_index(ids: list[str], documents: list[str]) -> BM25Index:
    """
    从 (id, document) 列表构建 BM25 索引。

    Args:
        ids: 文档 ID 列表
        documents: 文档内容列表（用于 BM25 的原始文本）
    """
    from rank_bm25 import BM25Okapi

    tokenized = [_tokenize(doc) for doc in documents]
    bm25 = BM25Okapi(tokenized)
    return BM25Index(ids=ids, bm25=bm25, tokenize_fn=_tokenize)
