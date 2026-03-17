"""
RAG 向量存储模块。

用途：存储和检索投资相关的书籍、论文、研报等长期知识。
这些知识不会过时（如价值投资理论、技术分析方法论），适合用 RAG 存储。

核心流程：
  文档原文 → 结构感知切分(Chunker) → 向量化(Embedding) → 存入 ChromaDB → 语义检索
  双层 chunk：小块召回，大块生成
  Embedding：BGE 中文 / Query Expansion + RRF 融合
"""

import hashlib
import os

import chromadb

from src.config.settings import DATA_DIR
from src.rag.chunker import chunk_document, infer_doc_type, ChunkResult, DocType
from src.rag.embedding import expand_query, get_embedding_function, reciprocal_rank_fusion


_client: chromadb.ClientAPI | None = None
_collection: chromadb.Collection | None = None

DB_PATH = str(DATA_DIR / "chroma_db")
# 集合名随 embedding 模型变化（维度不同，需隔离）
_COLLECTION_BGE = "investment_knowledge_bge"
_COLLECTION_DEFAULT = "investment_knowledge"


def _collection_name() -> str:
    return _COLLECTION_BGE if os.getenv("EMBEDDING_MODEL", "bge").lower() == "bge" else _COLLECTION_DEFAULT


def _get_collection() -> chromadb.Collection:
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=DB_PATH)
        emb_fn = get_embedding_function()
        kwargs = {"name": _collection_name(), "metadata": {"hnsw:space": "cosine"}}
        if emb_fn is not None:
            kwargs["embedding_function"] = emb_fn
        _collection = _client.get_or_create_collection(**kwargs)
    return _collection


def _make_id(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


def _chunk_result_to_metadata(cr: ChunkResult) -> dict:
    """ChunkResult 转 ChromaDB metadata，仅保留 ChromaDB 支持的类型。"""
    meta = {k: v for k, v in cr.metadata.items() if isinstance(v, (str, int, float, bool))}
    meta["section_title"] = meta.get("section_title", "") or ""
    meta["doc_type"] = meta.get("doc_type", "general") or "general"
    meta["block_type"] = meta.get("block_type", "paragraph") or "paragraph"
    return meta


def ingest_document(
    text: str,
    metadata: dict,
    doc_type: DocType | None = None,
) -> int:
    """
    将一篇文档写入向量数据库。

    使用结构感知切分：按标题/表格/段落分块，双层 chunk（小块召回、大块生成）。

    Args:
        text: 文档全文
        metadata: 元数据，如 {"source": "聪明的投资者", "file_type": ".pdf"}
        doc_type: 文档类型，None 时从 metadata 的 source 推断

    Returns:
        新增的片段数量
    """
    collection = _get_collection()
    if doc_type is None:
        doc_type = infer_doc_type(metadata.get("source", ""), text[:500])

    chunks = chunk_document(text, metadata, doc_type)
    if not chunks:
        return 0

    documents = []
    metadatas = []
    ids = []

    for cr in chunks:
        doc_id = _make_id(cr.content)
        documents.append(cr.content)
        meta = _chunk_result_to_metadata(cr)
        meta["parent_content"] = cr.parent_content[:4000]  # ChromaDB metadata 长度限制
        metadatas.append(meta)
        ids.append(doc_id)

    # 批量去重
    existing_ids = set()
    batch_size = 100
    for i in range(0, len(ids), batch_size):
        batch_ids = ids[i : i + batch_size]
        existing = collection.get(ids=batch_ids)
        existing_ids.update(existing.get("ids", []))

    to_add = [(d, m, i) for d, m, i in zip(documents, metadatas, ids) if i not in existing_ids]
    if not to_add:
        return 0

    batch_size = 100
    for i in range(0, len(to_add), batch_size):
        batch = to_add[i : i + batch_size]
        collection.add(
            documents=[b[0] for b in batch],
            metadatas=[b[1] for b in batch],
            ids=[b[2] for b in batch],
        )

    return len(to_add)


def search_knowledge(
    query: str,
    n_results: int = 5,
    use_query_expansion: bool | None = None,
    expansion_method: str = "simple",
) -> list[dict]:
    """
    语义检索：从知识库中找到与问题最相关的文档片段。

    - 双层 chunk：检索用小块，返回用大块（parent_content）
    - Query Expansion：可选扩写同义 query，多路检索后 RRF 融合

    Args:
        query: 检索问题，如"什么是安全边际"
        n_results: 返回结果数量
        use_query_expansion: 是否启用 query 扩展，None 时从 env ENABLE_QUERY_EXPANSION 读取
        expansion_method: "simple" 规则同义 | "llm" LLM 扩写
    """
    collection = _get_collection()

    if collection.count() == 0:
        return []

    if use_query_expansion is None:
        use_query_expansion = os.getenv("ENABLE_QUERY_EXPANSION", "1") == "1"

    if use_query_expansion:
        queries = expand_query(query, method=expansion_method, max_queries=3)
    else:
        queries = [query]

    if len(queries) == 1:
        # 单 query，直接检索
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )
        return _format_search_results(results, 0)

    # 多 query：分别检索，RRF 融合
    ranked_lists: list[list[tuple[str, float]]] = []
    raw_results = []

    for q in queries:
        r = collection.query(
            query_texts=[q],
            n_results=n_results * 2,  # 每路多取，融合后去重
            include=["documents", "metadatas", "distances"],
        )
        raw_results.append(r)
        ids = r.get("ids", [[]])[0]
        dists = r.get("distances", [[]])[0]
        ranked_lists.append(list(zip(ids, dists)))

    fused = reciprocal_rank_fusion(ranked_lists, k=60)
    top_ids = [doc_id for doc_id, _ in fused[:n_results]]

    if not top_ids:
        return []

    # 按 RRF 顺序获取完整文档
    fetched = collection.get(ids=top_ids, include=["documents", "metadatas"])
    id_to_doc = dict(zip(fetched["ids"], fetched["documents"]))
    id_to_meta = dict(zip(fetched["ids"], fetched["metadatas"]))
    id_to_rank = {doc_id: i for i, (doc_id, _) in enumerate(fused)}

    output = []
    for doc_id in top_ids:
        content = id_to_doc.get(doc_id, "")
        meta = id_to_meta.get(doc_id) or {}
        display_content = meta.get("parent_content") or content
        output.append({
            "content": display_content,
            "metadata": meta,
            "distance": 1 - (id_to_rank.get(doc_id, 0) / max(len(fused), 1)),  # 近似相关度
        })
    return output


def _format_search_results(results: dict, query_idx: int = 0) -> list[dict]:
    """将 ChromaDB 单 query 结果格式化为统一结构"""
    output = []
    docs = results.get("documents", [[]])[query_idx] or []
    metas = results.get("metadatas", [[]])[query_idx] or []
    dists = results.get("distances", [[]])[query_idx] if results.get("distances") else []
    for i in range(len(docs)):
        meta = metas[i] if i < len(metas) else {}
        content = docs[i] if i < len(docs) else ""
        display_content = meta.get("parent_content") or content
        output.append({
            "content": display_content,
            "metadata": meta,
            "distance": dists[i] if dists and i < len(dists) else None,
        })
    return output


def get_db_stats() -> dict:
    collection = _get_collection()
    return {
        "collection_name": _collection_name(),
        "total_documents": collection.count(),
        "db_path": DB_PATH,
    }


def list_sources() -> list[dict]:
    """列出知识库中所有不同的文件来源及其片段数量。"""
    collection = _get_collection()
    total = collection.count()
    if total == 0:
        return []

    all_data = collection.get(include=["metadatas"])
    source_map: dict[str, dict] = {}
    for meta in all_data["metadatas"]:
        src = meta.get("source", "unknown")
        if src not in source_map:
            source_map[src] = {
                "source": src,
                "file_type": meta.get("file_type", ""),
                "chunks": 0,
            }
        source_map[src]["chunks"] += 1

    return sorted(source_map.values(), key=lambda x: x["source"])


def delete_by_source(source_name: str) -> int:
    """删除知识库中指定来源的所有文档片段。返回被删除的数量。"""
    collection = _get_collection()
    before = collection.count()
    collection.delete(where={"source": source_name})
    after = collection.count()
    return before - after
