# RAG 评估系统

自动评估检索与生成质量，否则无法知道是否进步。

## 指标

| 指标 | 说明 |
|------|------|
| Recall@5 | 至少召回 1 个相关 doc 的 query 占比（Hit Rate） |
| Precision@5 | Top 5 中相关 doc 的比例 |
| MRR | 首个相关 doc 排名的倒数，取平均 |
| 生成正确率 | LLM 回答是否包含预期关键词（需 DEEPSEEK_API_KEY） |

## 用法

```bash
# 确保知识库已导入测试数据
python -m src.rag.ingest path/to/books/

# 运行评估
python -m eval.evaluation
```

## 文件说明

- `queries.json`：测试 query 列表
- `ground_truth.json`：每个 query 的相关标注
  - `relevant_keywords`：相关 doc 应包含的关键词
  - `relevant_sources`：相关 doc 的来源（文件名）
  - `expected_answer_keywords`：生成回答应包含的关键词

## 自定义

根据你的知识库内容，修改 `queries.json` 和 `ground_truth.json`。标注越准确，评估越有意义。
