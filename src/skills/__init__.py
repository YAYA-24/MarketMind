"""
Skills 桥接包。

SKILL 主文件位于项目本体 skills/ 目录，Cursor 通过 .cursor/skills/ 下的符号链接共用。
"""

import importlib.util
import re
from pathlib import Path

from src.config.settings import PROJECT_ROOT

# Skill 主目录（项目本体），.cursor/skills/ 通过符号链接指向此处
SKILLS_DIR = PROJECT_ROOT / "skills"

# Skill 注册表：skill_name (目录) -> script_name (脚本)，便于维护和校验
SKILL_REGISTRY = {
    "stock-data": "stock_data",
    "technical-analysis": "technical",
    "financial-data": "financial",
    "kline-chart": "kline_chart",
    "web-search": "web_search",
    "knowledge-rag": "knowledge_rag",
    "stock-monitor": "monitor_skill",
}


def _load(skill_name: str, script_name: str):
    """从 skills/<skill_name>/scripts/<script_name>.py 加载模块。

    Args:
        skill_name: 目录名（如 stock-data）
        script_name: 脚本名不含扩展名（如 stock_data）

    Returns:
        加载后的模块对象

    Raises:
        FileNotFoundError: 脚本文件不存在时
    """
    path = SKILLS_DIR / skill_name / "scripts" / f"{script_name}.py"
    if not path.exists():
        raise FileNotFoundError(
            f"Skill script not found: {path}\n"
            f"  Expected: skills/{skill_name}/scripts/{script_name}.py"
        )
    spec = importlib.util.spec_from_file_location(
        f"_skill_{script_name}", str(path.resolve())
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def get_skill_descriptions() -> str:
    """加载所有 Skill 的 description（来自 SKILL.md YAML frontmatter），与 Cursor 共用。

    用于注入 Agent system prompt，使项目本体与 Cursor IDE 使用相同的 Skill 定义。
    """
    lines = []
    for skill_name in SKILL_REGISTRY:
        path = SKILLS_DIR / skill_name / "SKILL.md"
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        # 解析 YAML frontmatter 中的 description（单行）
        match = re.search(r"^description:\s*(.+?)(?:\n|$)", text, re.MULTILINE)
        if match:
            desc = match.group(1).strip().strip("'\"")
            lines.append(f"- **{skill_name}**: {desc}")
    if not lines:
        return ""
    return "Skill 使用场景（与 Cursor 一致）：\n" + "\n".join(lines)
