"""Bridge → .cursor/skills/kline-chart/scripts/kline_chart.py"""
from src.skills import _load

_m = _load('kline-chart', 'kline_chart')
generate_kline_chart = _m.generate_kline_chart
KLINE_TOOLS = _m.KLINE_TOOLS
