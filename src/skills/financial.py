"""Bridge → skills/financial-data/scripts/"""
from src.skills import _load, SKILL_REGISTRY

_m = _load("financial-data", SKILL_REGISTRY["financial-data"])
get_financial_data = _m.get_financial_data
FINANCIAL_TOOLS = _m.FINANCIAL_TOOLS
