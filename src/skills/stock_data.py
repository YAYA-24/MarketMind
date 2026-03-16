"""Bridge → skills/stock-data/scripts/"""
from src.skills import _load, SKILL_REGISTRY

_m = _load("stock-data", SKILL_REGISTRY["stock-data"])
get_stock_price = _m.get_stock_price
get_multi_stock_prices = _m.get_multi_stock_prices
get_stock_history = _m.get_stock_history
ALL_TOOLS = _m.ALL_TOOLS
