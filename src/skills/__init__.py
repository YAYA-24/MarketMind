"""
Skills 桥接包。

实际的 Skill 脚本已迁移至 .cursor/skills/*/scripts/，
本包通过动态加载保持原有 import 路径不变。
"""

import importlib.util
import os

_SKILLS_BASE = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', '..', '.cursor', 'skills')
)


def _load(skill_name: str, script_name: str):
    """从 .cursor/skills/<skill_name>/scripts/<script_name>.py 加载模块。"""
    path = os.path.join(_SKILLS_BASE, skill_name, 'scripts', f'{script_name}.py')
    spec = importlib.util.spec_from_file_location(
        f'_skill_{script_name}', os.path.abspath(path)
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
