---
name: knowledge-rag
description: Retrieve investment knowledge from the RAG vector database containing books, papers, and research reports. Use when the user asks about investment theory, analysis frameworks, valuation methods, or professional investment concepts like margin of safety, DCF, or moat analysis.
---

# 投资知识库检索 (RAG)

从 ChromaDB 向量数据库中语义检索投资书籍、论文中的专业知识。

## Tools

| Tool | 功能 | 参数 |
|------|------|------|
| `search_investment_knowledge` | 语义检索知识库 | `query`: 检索问题 |
| `get_knowledge_db_info` | 查看知识库状态 | 无参数 |

## 与联网搜索的分工

- **联网搜索** → 最新新闻、实时动态（时效性信息）
- **知识库 RAG** → 投资理论、分析方法（静态专业知识）

## 知识库管理

导入文档（支持 PDF/TXT/MD）：

```bash
python -m src.rag.ingest path/to/book.pdf
python -m src.rag.ingest data/books/
python -m src.rag.ingest --stats
```

## RAG 管线

文档 → 结构感知切分 → BGE 中文 Embedding → ChromaDB(cosine) → Query Expansion + RRF 融合

**Embedding：** BAAI/bge-small-zh-v1.5（中文优化）。环境变量 `EMBEDDING_MODEL=bge`（默认）或 `default`。

**混合检索：** Dense top 50 + BM25 top 50 → 合并去重 → RRF 融合。金融领域对「ROE」「净利润同比」「现金流」等关键词敏感，BM25 与向量互补。`ENABLE_HYBRID_SEARCH=1` 启用。

**Query Expansion：** 可选扩写同义 query。`ENABLE_QUERY_EXPANSION=1` 启用。

**切分策略：** 按标题/表格/段落，双层 chunk（小块召回、大块生成）。

## 脚本

实现文件：[scripts/knowledge_rag.py](scripts/knowledge_rag.py)

导出：`KNOWLEDGE_RAG_TOOLS` 列表
