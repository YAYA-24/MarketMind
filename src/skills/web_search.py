"""Bridge → .cursor/skills/web-search/scripts/web_search.py"""
from src.skills import _load

_m = _load('web-search', 'web_search')
search_web = _m.search_web
search_stock_news = _m.search_stock_news
WEB_SEARCH_TOOLS = _m.WEB_SEARCH_TOOLS
