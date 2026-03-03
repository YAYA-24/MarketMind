"""Bridge → .cursor/skills/financial-data/scripts/financial.py"""
from src.skills import _load

_m = _load('financial-data', 'financial')
get_financial_data = _m.get_financial_data
FINANCIAL_TOOLS = _m.FINANCIAL_TOOLS
