"""Bridge → skills/web-search/scripts/"""
from src.skills import _load, SKILL_REGISTRY

_m = _load("web-search", SKILL_REGISTRY["web-search"])
search_web = _m.search_web
search_stock_news = _m.search_stock_news
WEB_SEARCH_TOOLS = _m.WEB_SEARCH_TOOLS
