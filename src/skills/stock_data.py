"""Bridge → .cursor/skills/stock-data/scripts/stock_data.py"""
from src.skills import _load

_m = _load('stock-data', 'stock_data')
get_stock_price = _m.get_stock_price
get_multi_stock_prices = _m.get_multi_stock_prices
get_stock_history = _m.get_stock_history
ALL_TOOLS = _m.ALL_TOOLS
