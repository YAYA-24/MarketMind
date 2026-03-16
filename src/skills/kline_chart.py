"""Bridge → skills/kline-chart/scripts/"""
from src.skills import _load, SKILL_REGISTRY

_m = _load("kline-chart", SKILL_REGISTRY["kline-chart"])
generate_kline_chart = _m.generate_kline_chart
KLINE_TOOLS = _m.KLINE_TOOLS
