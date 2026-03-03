"""Bridge → .cursor/skills/knowledge-rag/scripts/news_rag.py"""
from src.skills import _load

_m = _load('knowledge-rag', 'news_rag')
search_investment_knowledge = _m.search_investment_knowledge
get_knowledge_db_info = _m.get_knowledge_db_info
KNOWLEDGE_RAG_TOOLS = _m.KNOWLEDGE_RAG_TOOLS
