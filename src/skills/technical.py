"""Bridge → skills/technical-analysis/scripts/"""
from src.skills import _load, SKILL_REGISTRY

_m = _load("technical-analysis", SKILL_REGISTRY["technical-analysis"])
get_technical_indicators = _m.get_technical_indicators
TECHNICAL_TOOLS = _m.TECHNICAL_TOOLS
