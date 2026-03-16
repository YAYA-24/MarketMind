"""
A 股分析 Agent 的核心图定义。

工具来源：
  - 自有 Skills（行情/技术/财务/K线/知识库/监控）
  - 外部 MCP Server（Tavily 联网搜索，通过 langchain-mcp-adapters 接入）
  - 降级：若 MCP 不可用，回退到直接 SDK 调用
"""

from typing import Annotated, Literal
from typing_extensions import TypedDict

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from src.config.settings import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    SYSTEM_PROMPT,
)
from src.skills import get_skill_descriptions
from src.skills.stock_data import ALL_TOOLS as STOCK_TOOLS
from src.skills.knowledge_rag import KNOWLEDGE_RAG_TOOLS
from src.skills.technical import TECHNICAL_TOOLS
from src.skills.financial import FINANCIAL_TOOLS
from src.skills.kline_chart import KLINE_TOOLS
from src.skills.monitor_skill import MONITOR_TOOLS

BASE_TOOLS = (
    STOCK_TOOLS
    + TECHNICAL_TOOLS
    + FINANCIAL_TOOLS
    + KLINE_TOOLS
    + KNOWLEDGE_RAG_TOOLS
    + MONITOR_TOOLS
)


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


_active_tools: list = []


def build_llm():
    llm = ChatOpenAI(
        model=DEEPSEEK_MODEL,
        base_url=DEEPSEEK_BASE_URL,
        api_key=DEEPSEEK_API_KEY,
        temperature=0.3,
    )
    return llm.bind_tools(_active_tools)


def chatbot(state: AgentState) -> dict:
    llm = build_llm()
    messages = state["messages"]
    if not messages or not isinstance(messages[0], SystemMessage):
        prompt = SYSTEM_PROMPT
        skill_desc = get_skill_descriptions()
        if skill_desc:
            prompt = prompt + "\n\n" + skill_desc
        messages = [SystemMessage(content=prompt)] + list(messages)
    response = llm.invoke(messages)
    return {"messages": [response]}


def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return "__end__"


def build_graph(mcp_tools=None):
    """构建 Agent 图。

    Args:
        mcp_tools: 从外部 MCP Server 获取的工具列表。
                   若提供，替代内置的 WEB_SEARCH_TOOLS。
                   若为 None，降级使用直接 SDK 调用。
    """
    global _active_tools

    if mcp_tools:
        _active_tools = list(BASE_TOOLS) + list(mcp_tools)
    else:
        from src.skills.web_search import WEB_SEARCH_TOOLS
        _active_tools = list(BASE_TOOLS) + list(WEB_SEARCH_TOOLS)

    graph = StateGraph(AgentState)
    tool_node = ToolNode(_active_tools)
    graph.add_node("chatbot", chatbot)
    graph.add_node("tools", tool_node)
    graph.add_edge(START, "chatbot")
    graph.add_conditional_edges("chatbot", should_continue)
    graph.add_edge("tools", "chatbot")
    return graph.compile()
