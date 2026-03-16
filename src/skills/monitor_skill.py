"""Bridge → skills/stock-monitor/scripts/"""
from src.skills import _load, SKILL_REGISTRY

_m = _load("stock-monitor", SKILL_REGISTRY["stock-monitor"])
add_stock_monitor = _m.add_stock_monitor
list_stock_monitors = _m.list_stock_monitors
remove_stock_monitor = _m.remove_stock_monitor
MONITOR_TOOLS = _m.MONITOR_TOOLS
