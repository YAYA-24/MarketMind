"""
RAG 评估系统。

指标：Recall@5、Precision@5、MRR、生成正确率
用法：python -m eval.evaluation
"""

import json
import os
import sys
from pathlib import Path

# 项目根目录
EVAL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EVAL_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _load_queries() -> list[dict]:
    with open(EVAL_DIR / "queries.json", "r", encoding="utf-8") as f:
        return json.load(f)


def _load_ground_truth() -> dict:
    with open(EVAL_DIR / "ground_truth.json", "r", encoding="utf-8") as f:
        return json.load(f)


def _is_relevant(doc: dict, gt: dict) -> bool:
    """判断单个文档是否相关"""
    content = (doc.get("content") or "").lower()
    meta = doc.get("metadata") or {}
    source = (meta.get("source") or "").lower()

    keywords = [k.lower() for k in gt.get("relevant_keywords", [])]
    sources = [s.lower() for s in gt.get("relevant_sources", [])]

    if keywords and any(kw in content for kw in keywords):
        return True
    if sources and source and any(s in source for s in sources):
        return True
    return False


def _compute_retrieval_metrics(queries: list[dict], ground_truth: dict) -> dict:
    """计算检索指标：Recall@5、Precision@5、MRR"""
    from src.rag.vector_store import search_knowledge

    recall_sum = 0.0
    precision_sum = 0.0
    mrr_sum = 0.0
    n = 0

    for q in queries:
        qid = q.get("id", "")
        query = q.get("query", "")
        gt = ground_truth.get(qid, {})
        if not gt:
            continue

        results = search_knowledge(query, n_results=5)
        if not results:
            recall_sum += 0.0
            precision_sum += 0.0
            mrr_sum += 0.0
            n += 1
            continue

        # 二值相关性：每个 doc 是否 relevant（含 keyword 或 source）
        relevant_retrieved = sum(1 for r in results if _is_relevant(r, gt))

        # Recall@5：至少召回 1 个相关 doc 的 query 占比（Hit Rate）
        recall_at_5 = 1.0 if relevant_retrieved >= 1 else 0.0
        recall_sum += recall_at_5

        # Precision@5 = |relevant ∩ retrieved@5| / 5
        precision_at_5 = relevant_retrieved / 5.0
        precision_sum += precision_at_5

        # MRR: 1/rank of first relevant doc
        rr = 0.0
        for rank, r in enumerate(results, 1):
            if _is_relevant(r, gt):
                rr = 1.0 / rank
                break
        mrr_sum += rr
        n += 1

    if n == 0:
        return {"recall_at_5": 0, "precision_at_5": 0, "mrr": 0}

    return {
        "recall_at_5": recall_sum / n,
        "precision_at_5": precision_sum / n,
        "mrr": mrr_sum / n,
    }


def _compute_generation_accuracy(queries: list[dict], ground_truth: dict) -> float:
    """生成正确率：检查 LLM 回答是否包含预期关键词"""
    from src.rag.vector_store import search_knowledge
    from src.rag.context_builder import build_context

    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        return -1.0  # 未安装时跳过

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("  跳过生成正确率：未设置 DEEPSEEK_API_KEY")
        return -1.0

    llm = ChatOpenAI(
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        openai_api_key=api_key,
        openai_api_base=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    )

    correct = 0
    n = 0

    for q in queries:
        qid = q.get("id", "")
        query = q.get("query", "")
        gt = ground_truth.get(qid, {})
        expected = [k.lower() for k in gt.get("expected_answer_keywords", [])]
        if not expected:
            continue

        results = search_knowledge(query, n_results=5)
        if not results:
            n += 1
            continue

        context = build_context(results, query=query, token_budget=3000)
        prompt = f"""基于以下检索到的知识回答问题。只根据给定内容回答，不要编造。

{context}

问题：{query}

请简洁回答："""

        try:
            resp = llm.invoke(prompt)
            answer = (resp.content if hasattr(resp, "content") else str(resp)).lower()
            hit = sum(1 for kw in expected if kw in answer)
            if hit >= len(expected) * 0.5:  # 至少覆盖一半预期关键词
                correct += 1
        except Exception:
            pass
        n += 1

    return correct / n if n > 0 else 0.0


def main():
    print("=" * 50)
    print("  RAG 评估")
    print("=" * 50)

    queries = _load_queries()
    ground_truth = _load_ground_truth() if (EVAL_DIR / "ground_truth.json").exists() else {}

    if not ground_truth:
        print("警告：ground_truth.json 为空，请补充相关标注")

    print(f"\n测试集：{len(queries)} 个 query")
    print("\n检索指标（需知识库有数据）...")

    try:
        metrics = _compute_retrieval_metrics(queries, ground_truth)
        print(f"\n  Recall@5:    {metrics['recall_at_5']:.4f}")
        print(f"  Precision@5: {metrics['precision_at_5']:.4f}")
        print(f"  MRR:         {metrics['mrr']:.4f}")
    except Exception as e:
        print(f"  检索评估失败: {e}")
        metrics = {}

    print("\n生成正确率（需 DEEPSEEK_API_KEY）...")
    gen_acc = _compute_generation_accuracy(queries, ground_truth)
    if gen_acc >= 0:
        print(f"  生成正确率: {gen_acc:.4f}")
        metrics["generation_accuracy"] = gen_acc
    else:
        print("  已跳过")

    print("\n" + "=" * 50)
    return metrics


if __name__ == "__main__":
    main()
