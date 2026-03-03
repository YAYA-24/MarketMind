"""Bridge → .cursor/skills/stock-monitor/scripts/monitor_skill.py"""
from src.skills import _load

_m = _load('stock-monitor', 'monitor_skill')
add_stock_monitor = _m.add_stock_monitor
list_stock_monitors = _m.list_stock_monitors
remove_stock_monitor = _m.remove_stock_monitor
MONITOR_TOOLS = _m.MONITOR_TOOLS
