"""
RAG 向量存储模块。

用途：存储和检索投资相关的书籍、论文、研报等长期知识。
这些知识不会过时（如价值投资理论、技术分析方法论），适合用 RAG 存储。

核心流程：
  文档原文 → 文本切分(Chunking) → 向量化(Embedding) → 存入 ChromaDB → 语义检索
"""

import hashlib
import chromadb


_client: chromadb.ClientAPI | None = None
_collection: chromadb.Collection | None = None

DB_PATH = "./data/chroma_db"
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


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """
    将长文本切分为重叠的小片段。

    对于书籍/论文，用更大的 chunk_size（500字）保留更多上下文。
    overlap=100 确保关键段落不会被切断。
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start = end - overlap

    return chunks


def ingest_document(text: str, metadata: dict) -> int:
    """
    将一篇文档写入向量数据库。

    Args:
        text: 文档全文
        metadata: 元数据，如 {"source": "聪明的投资者", "author": "格雷厄姆", "type": "book"}

    Returns:
        新增的片段数量
    """
    collection = _get_collection()
    chunks = _chunk_text(text)

    documents = []
    metadatas = []
    ids = []

    for i, chunk in enumerate(chunks):
        doc_id = _make_id(chunk)

        existing = collection.get(ids=[doc_id])
        if existing and existing["ids"]:
            continue

        documents.append(chunk)
        metadatas.append({
            **metadata,
            "chunk_index": i,
            "total_chunks": len(chunks),
        })
        ids.append(doc_id)

    if not documents:
        return 0

    batch_size = 100
    for i in range(0, len(documents), batch_size):
        collection.add(
            documents=documents[i:i + batch_size],
            metadatas=metadatas[i:i + batch_size],
            ids=ids[i:i + batch_size],
        )

    return len(documents)


def search_knowledge(query: str, n_results: int = 5) -> list[dict]:
    """
    语义检索：从知识库中找到与问题最相关的文档片段。

    Args:
        query: 检索问题，如"什么是安全边际"
        n_results: 返回结果数量
    """
    collection = _get_collection()

    if collection.count() == 0:
        return []

    results = collection.query(query_texts=[query], n_results=n_results)

    output = []
    for i in range(len(results["documents"][0])):
        output.append({
            "content": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
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
