"""Bridge → skills/knowledge-rag/scripts/"""
from src.skills import _load, SKILL_REGISTRY

_m = _load("knowledge-rag", SKILL_REGISTRY["knowledge-rag"])
search_investment_knowledge = _m.search_investment_knowledge
get_knowledge_db_info = _m.get_knowledge_db_info
KNOWLEDGE_RAG_TOOLS = _m.KNOWLEDGE_RAG_TOOLS
