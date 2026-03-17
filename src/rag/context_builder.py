"""
RAG 上下文构建模块。

优化注入 LLM 的 context：按相关度排序、去重、控制 token budget、标注来源。
格式：[Source | 时间/类型]\n内容\n\n
减少 LLM 幻觉。
"""

# 中文约 1.5 字符/token
CHARS_PER_TOKEN = 1.5
DEFAULT_TOKEN_BUDGET = 4000


def _estimate_tokens(text: str) -> int:
    """粗略估计 token 数"""
    return int(len(text) / CHARS_PER_TOKEN)


def _format_source_label(meta: dict) -> str:
    """
    生成来源标签：[Source | 时间/类型]
    例如：[贵州茅台年报 | 2025 Q1 财报]、[财经快讯 | 2024-01-15 新闻]
    """
    source = meta.get("source", "未知来源")
    doc_type = meta.get("doc_type", "general")
    time_str = meta.get("time", "")

    type_label = {
        "report": "研报",
        "news": "新闻",
        "book": "书籍",
        "general": "文档",
    }.get(doc_type, "文档")

    if time_str:
        return f"[{source} | {time_str} {type_label}]"
    return f"[{source} | {type_label}]"


def _content_hash(content: str, max_len: int = 200) -> str:
    """用于去重的内容指纹（取前 N 字）"""
    return content[:max_len].strip()


def build_context(
    results: list[dict],
    query: str = "",
    token_budget: int = DEFAULT_TOKEN_BUDGET,
    dedupe: bool = True,
    include_header: bool = True,
) -> str:
    """
    将检索结果构建为 LLM 可用的 context。

    Args:
        results: search_knowledge 返回的列表，每项含 content、metadata、distance
        query: 检索问题（用于 header）
        token_budget: 最大 token 数
        dedupe: 是否按内容去重
        include_header: 是否包含「检索到 N 段内容」的 header

    Returns:
        格式化后的 context 字符串
    """
    if not results:
        return ""

    # 1. 按相关度排序（results 已从 rerank 排序，distance 越大越相关）
    sorted_results = sorted(
        results,
        key=lambda r: r.get("distance") or 0,
        reverse=True,
    )

    # 2. 去重（按内容指纹）
    if dedupe:
        seen = set()
        unique = []
        for r in sorted_results:
            fp = _content_hash(r.get("content", ""))
            if fp and fp not in seen:
                seen.add(fp)
                unique.append(r)
        sorted_results = unique

    # 3. 控制 token budget
    lines = []
    used_tokens = 0
    budget = token_budget

    if include_header and query:
        header = f"从知识库中检索到与「{query}」相关的内容：\n\n"
        lines.append(header)
        used_tokens += _estimate_tokens(header)

    for r in sorted_results:
        content = r.get("content", "").strip()
        if not content:
            continue

        label = _format_source_label(r.get("metadata") or {})
        block = f"{label}\n{content}\n\n"
        block_tokens = _estimate_tokens(block)

        if used_tokens + block_tokens > budget:
            # 截断当前块以适配 budget
            remaining = int((budget - used_tokens) * CHARS_PER_TOKEN) - len(label) - 4
            if remaining > 100:
                truncated = content[:remaining] + "…"
                block = f"{label}\n{truncated}\n\n"
                lines.append(block)
            break

        lines.append(block)
        used_tokens += block_tokens

    return "".join(lines).strip()
