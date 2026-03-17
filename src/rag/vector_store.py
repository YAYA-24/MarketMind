"""
RAG 向量存储模块。

用途：存储和检索投资相关的书籍、论文、研报等长期知识。
这些知识不会过时（如价值投资理论、技术分析方法论），适合用 RAG 存储。

核心流程：
  文档原文 → 结构感知切分(Chunker) → 向量化(Embedding) → 存入 ChromaDB → 语义检索
  双层 chunk：小块召回，大块生成
"""

import hashlib
import chromadb

from src.config.settings import DATA_DIR
from src.rag.chunker import chunk_document, infer_doc_type, ChunkResult, DocType


_client: chromadb.ClientAPI | None = None
_collection: chromadb.Collection | None = None

DB_PATH = str(DATA_DIR / "chroma_db")
COLLECTION_NAME = "investment_knowledge"


def _get_collection() -> chromadb.Collection:
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=DB_PATH)
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
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


def search_knowledge(query: str, n_results: int = 5) -> list[dict]:
    """
    语义检索：从知识库中找到与问题最相关的文档片段。

    双层 chunk：检索用小块，返回用大块（parent_content）以提供更多上下文。

    Args:
        query: 检索问题，如"什么是安全边际"
        n_results: 返回结果数量
    """
    collection = _get_collection()

    if collection.count() == 0:
        return []

    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    output = []
    for i in range(len(results["documents"][0])):
        meta = results["metadatas"][0][i] or {}
        content = results["documents"][0][i]
        # 优先返回大块（parent_content）供 LLM 生成，无则用小块
        display_content = meta.get("parent_content") or content
        output.append({
            "content": display_content,
            "metadata": meta,
            "distance": results["distances"][0][i] if results.get("distances") else None,
        })

    return output


def get_db_stats() -> dict:
    collection = _get_collection()
    return {
        "collection_name": COLLECTION_NAME,
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
