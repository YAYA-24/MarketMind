"""Bridge → .cursor/skills/technical-analysis/scripts/technical.py"""
from src.skills import _load

_m = _load('technical-analysis', 'technical')
get_technical_indicators = _m.get_technical_indicators
TECHNICAL_TOOLS = _m.TECHNICAL_TOOLS
