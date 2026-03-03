"""
知识库导入脚本。

用法:
  导入单个 PDF:     python -m src.rag.ingest path/to/book.pdf
  导入单个文本文件:  python -m src.rag.ingest path/to/notes.txt
  导入整个目录:     python -m src.rag.ingest path/to/books/
  查看知识库状态:   python -m src.rag.ingest --stats

支持的格式: .pdf, .txt, .md
"""

import sys
import os
from pathlib import Path
from src.rag.vector_store import ingest_document, get_db_stats


def extract_text_from_pdf(filepath: str) -> str:
    """从 PDF 文件提取文本内容。"""
    import fitz  # pymupdf
    doc = fitz.open(filepath)
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    return "\n".join(pages)


def extract_text_from_file(filepath: str) -> str:
    """根据文件类型提取文本。"""
    ext = Path(filepath).suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(filepath)
    elif ext in (".txt", ".md"):
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    else:
        raise ValueError(f"不支持的文件格式: {ext}（支持 .pdf, .txt, .md）")


def ingest_file(filepath: str) -> int:
    """导入单个文件到知识库。"""
    path = Path(filepath)
    print(f"  正在处理: {path.name}")

    text = extract_text_from_file(str(path))
    if not text.strip():
        print(f"  跳过（内容为空）: {path.name}")
        return 0

    metadata = {
        "source": path.name,
        "file_type": path.suffix.lower(),
        "file_path": str(path.absolute()),
    }

    added = ingest_document(text, metadata)
    print(f"  完成: 新增 {added} 个片段")
    return added


def ingest_directory(dirpath: str) -> int:
    """导入目录下所有支持的文件。"""
    total = 0
    supported = {".pdf", ".txt", ".md"}

    for path in sorted(Path(dirpath).rglob("*")):
        if path.suffix.lower() in supported:
            total += ingest_file(str(path))

    return total


def main():
    args = sys.argv[1:]

    if not args or "--help" in args:
        print(__doc__)
        return

    if "--stats" in args:
        stats = get_db_stats()
        print(f"知识库状态:")
        print(f"  集合名称: {stats['collection_name']}")
        print(f"  文档片段总数: {stats['total_documents']}")
        print(f"  存储路径: {stats['db_path']}")
        return

    print("=" * 50)
    print("  导入文档到投资知识库")
    print("=" * 50)

    total_added = 0
    for target in args:
        if os.path.isdir(target):
            print(f"\n处理目录: {target}")
            total_added += ingest_directory(target)
        elif os.path.isfile(target):
            total_added += ingest_file(target)
        else:
            print(f"  路径不存在: {target}")

    stats = get_db_stats()
    print(f"\n导入完成！新增 {total_added} 个片段")
    print(f"知识库当前共 {stats['total_documents']} 个片段")


if __name__ == "__main__":
    main()
