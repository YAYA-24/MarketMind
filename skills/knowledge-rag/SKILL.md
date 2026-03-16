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

文档 → 切分(500字/100字重叠) → Embedding(all-MiniLM-L6-v2) → ChromaDB(cosine) → 语义检索

## 脚本

实现文件：[scripts/knowledge_rag.py](scripts/knowledge_rag.py)

导出：`KNOWLEDGE_RAG_TOOLS` 列表
