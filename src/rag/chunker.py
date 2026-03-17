"""
结构感知文档切分模块。

解决固定字符切分导致的语义断裂、碎片化问题：
- 按标题/章节分块
- 表格单独处理
- 保留元数据（时间、公司、来源）
- 双层 chunk：小块召回、大块生成

金融场景策略：
- 财报/书籍：按章节切
- 新闻：按段落+时间切
- 研报：按分析逻辑块切
"""

import re
from dataclasses import dataclass
from typing import Literal

DocType = Literal["book", "report", "news", "general"]


@dataclass
class ChunkResult:
    """单个 chunk 结果（用于召回的小块）"""
    content: str           # 小块内容，用于 embedding 和检索
    parent_content: str    # 大块内容，用于 LLM 生成
    metadata: dict        # section_title, doc_type, chunk_index 等


# 中文约 1 token ≈ 1.5 字符
SMALL_CHUNK_CHARS = 350   # ~200 tokens，召回用
LARGE_CHUNK_CHARS = 1200  # ~800 tokens，生成用
OVERLAP_SMALL = 80
OVERLAP_LARGE = 150

# 标题/章节正则
HEADER_PATTERNS = [
    r"^#{1,6}\s+.+$",                    # Markdown: ## 标题
    r"^第[一二三四五六七八九十百千\d]+[章章节部分篇]\s*.+$",  # 第X章
    r"^[一二三四五六七八九十]+[、．.]\s*.+$",              # 一、二、三、
    r"^[（(][一二三四五六七八九十]+[)）]\s*.+$",           # （一）（二）
    r"^\d+[．.]\s*.+$",                   # 1. 2. 3.
    r"^\d+[、]\s*.+$",                    # 1、2、3、
    r"^[（(]\d+[)）]\s*.+$",              # （1）（2）
]

# 时间戳模式（新闻用）
TIME_PATTERN = re.compile(
    r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?|\d{4}[-/]\d{1,2}[-/]\d{1,2}|"
    r"\d{1,2}月\d{1,2}日|\d{2}:\d{2}(?::\d{2})?)"
)


def _is_header(line: str) -> bool:
    """判断是否为标题行"""
    line = line.strip()
    if not line or len(line) > 80:
        return False
    for pat in HEADER_PATTERNS:
        if re.match(pat, line):
            return True
    return False


def _is_table_row(line: str) -> bool:
    """判断是否为表格行（| 分隔或制表符分隔）"""
    line = line.strip()
    if not line:
        return False
    # Markdown 表格或制表符
    if "|" in line and line.count("|") >= 2:
        return True
    if "\t" in line and line.count("\t") >= 2:
        return True
    return False


def _extract_time(text: str) -> str | None:
    """从文本中提取首个时间戳"""
    m = TIME_PATTERN.search(text)
    return m.group(1) if m else None


def _extract_company(text: str) -> str | None:
    """简单启发式：提取可能的公司名（6字以内、常见后缀）"""
    # 常见公司后缀
    suffix = r"(股份|集团|科技|证券|银行|保险|基金|有限|公司)"
    m = re.search(rf"([\u4e00-\u9fa5]{{2,6}}{suffix})", text)
    return m.group(1) if m else None


def _split_by_semantic_boundary(text: str, max_size: int, overlap: int) -> list[str]:
    """按语义边界切分：优先段落、句子"""
    if len(text) <= max_size:
        return [text] if text.strip() else []

    separators = ["\n\n\n", "\n\n", "\n", "。", "；", "！", "，", " "]
    chunks = []
    remaining = text

    while remaining and len(remaining) > max_size:
        chunk = remaining[: max_size + 100]  # 多取一点以便找分隔符
        best_pos = -1
        best_sep = ""

        for sep in separators:
            pos = chunk.rfind(sep)
            if pos > max_size // 2:  # 至少保留一半内容
                best_pos = pos + len(sep)
                best_sep = sep
                break

        if best_pos > 0:
            piece = remaining[:best_pos].strip()
            remaining = remaining[best_pos:]
        else:
            piece = remaining[:max_size]
            remaining = remaining[max_size - overlap :]

        if piece:
            chunks.append(piece)

        # overlap
        if remaining and overlap > 0:
            overlap_text = remaining[:overlap]
            remaining = overlap_text + remaining[overlap:]

    if remaining.strip():
        chunks.append(remaining.strip())

    return chunks


def _parse_into_blocks(text: str, doc_type: DocType) -> list[dict]:
    """
    将文档解析为结构块：header, paragraph, table
    每个 block 含 {type, content, title, metadata}
    """
    lines = text.split("\n")
    blocks = []
    i = 0
    current_title = ""

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # 表格：连续表格行合并
        if _is_table_row(line):
            table_lines = []
            while i < len(lines) and _is_table_row(lines[i]):
                table_lines.append(lines[i])
                i += 1
            table_content = "\n".join(table_lines)
            blocks.append({
                "type": "table",
                "content": table_content,
                "title": current_title,
                "metadata": {},
            })
            continue

        # 标题
        if _is_header(line):
            current_title = stripped
            # 标题与后续段落合并（除非下一行也是标题）
            content_parts = [stripped]
            i += 1
            while i < len(lines):
                next_line = lines[i]
                if _is_header(next_line) or _is_table_row(next_line):
                    break
                if next_line.strip():
                    content_parts.append(next_line)
                i += 1
            blocks.append({
                "type": "header_section",
                "content": "\n".join(content_parts),
                "title": current_title,
                "metadata": {},
            })
            continue

        # 普通段落
        para_lines = []
        while i < len(lines):
            if _is_header(lines[i]) or _is_table_row(lines[i]):
                break
            para_lines.append(lines[i])
            i += 1
        para_content = "\n".join(para_lines).strip()
        if para_content:
            meta = {}
            if doc_type == "news":
                t = _extract_time(para_content)
                if t:
                    meta["time"] = t
                c = _extract_company(para_content)
                if c:
                    meta["company"] = c
            blocks.append({
                "type": "paragraph",
                "content": para_content,
                "title": current_title,
                "metadata": meta,
            })

    return blocks


def _blocks_to_two_tier_chunks(
    blocks: list[dict],
    base_metadata: dict,
    doc_type: DocType,
) -> list[ChunkResult]:
    """
    将结构块转为双层 chunk：
    - 小块（~350 字）用于召回
    - 大块（~1200 字）用于生成

    策略：先按块积累成大块，再对大块做语义切分得到小块；每个小块携带所属大块作为 parent_content。
    """
    results = []
    chunk_index = 0

    # 第一轮：按 LARGE_CHUNK_CHARS 积累成大块
    large_chunks = []
    buf: list[str] = []
    buf_len = 0

    for block in blocks:
        content = block["content"]
        title = block.get("title", "")
        block_type = block["type"]

        # 表格：整体保留，不拆分
        if block_type == "table":
            if buf and buf_len + len(content) > LARGE_CHUNK_CHARS:
                large_chunks.append({"content": "\n\n".join(buf), "title": "", "type": "mixed"})
                buf, buf_len = [], 0
            large_chunks.append({"content": content, "title": title, "type": "table"})
            continue

        # 段落/章节
        if buf_len + len(content) + 2 > LARGE_CHUNK_CHARS and buf:
            large_chunks.append({"content": "\n\n".join(buf), "title": title, "type": "paragraph"})
            buf, buf_len = [], 0
        buf.append(content)
        buf_len += len(content) + 2

    if buf:
        large_chunks.append({"content": "\n\n".join(buf), "title": "", "type": "paragraph"})

    # 第二轮：每个大块切分为小块，小块用于召回，大块用于生成
    for lc in large_chunks:
        parent_content = lc["content"]
        if len(parent_content) > LARGE_CHUNK_CHARS:
            parent_content = parent_content[:LARGE_CHUNK_CHARS] + "…"

        if lc["type"] == "table":
            # 表格不切分，整块作为一个小块
            small_content = lc["content"][:SMALL_CHUNK_CHARS * 2]  # 表格可稍大
            results.append(ChunkResult(
                content=small_content,
                parent_content=lc["content"],
                metadata={
                    **base_metadata,
                    "section_title": lc["title"],
                    "doc_type": doc_type,
                    "chunk_index": chunk_index,
                    "block_type": "table",
                },
            ))
            chunk_index += 1
        else:
            small_parts = _split_by_semantic_boundary(
                lc["content"], SMALL_CHUNK_CHARS, OVERLAP_SMALL
            )
            for sp in small_parts:
                if sp.strip():
                    results.append(ChunkResult(
                        content=sp,
                        parent_content=parent_content,
                        metadata={
                            **base_metadata,
                            "section_title": lc["title"],
                            "doc_type": doc_type,
                            "chunk_index": chunk_index,
                            "block_type": lc["type"],
                        },
                    ))
                    chunk_index += 1

    return results


def chunk_document(
    text: str,
    metadata: dict,
    doc_type: DocType = "general",
) -> list[ChunkResult]:
    """
    结构感知切分入口。

    Args:
        text: 文档全文
        metadata: 基础元数据（source, file_type 等）
        doc_type: 文档类型，影响切分策略
          - book: 按章节，适合投资书籍
          - report: 按分析逻辑块，适合研报
          - news: 按段落+时间，适合新闻
          - general: 通用语义切分

    Returns:
        ChunkResult 列表，每个含 content（召回用）、parent_content（生成用）、metadata
    """
    text = text.strip()
    if not text:
        return []

    blocks = _parse_into_blocks(text, doc_type)

    if not blocks:
        # 无结构时退化为语义切分
        small_parts = _split_by_semantic_boundary(
            text, SMALL_CHUNK_CHARS, OVERLAP_SMALL
        )
        large_parts = _split_by_semantic_boundary(
            text, LARGE_CHUNK_CHARS, OVERLAP_LARGE
        )
        results = []
        for i, sp in enumerate(small_parts):
            # 找到包含此小块的大块
            parent = ""
            for lp in large_parts:
                if sp in lp or (len(sp) > 100 and sp[:100] in lp):
                    parent = lp
                    break
            if not parent and large_parts:
                idx = min(i * len(large_parts) // len(small_parts), len(large_parts) - 1)
                parent = large_parts[idx]
            results.append(ChunkResult(
                content=sp,
                parent_content=parent or sp,
                metadata={
                    **metadata,
                    "section_title": "",
                    "doc_type": doc_type,
                    "chunk_index": i,
                    "block_type": "paragraph",
                },
            ))
        return results

    return _blocks_to_two_tier_chunks(blocks, metadata, doc_type)


def infer_doc_type(filename: str, text_preview: str = "") -> DocType:
    """
    从文件名和内容预览推断文档类型。
    """
    name_lower = filename.lower()
    if "财报" in name_lower or "年报" in name_lower or "季报" in name_lower:
        return "report"
    if "研报" in name_lower or "分析" in name_lower or "策略" in name_lower:
        return "report"
    if "新闻" in name_lower or "快讯" in name_lower:
        return "news"
    if any(x in name_lower for x in [".md", "笔记", "note"]):
        return "general"
    # 书籍通常为 pdf，且无上述关键词
    if ".pdf" in name_lower:
        return "book"
    return "general"
