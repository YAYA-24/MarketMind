"""
A 股分析 Agent — FastAPI 后端

提供：
  - SSE 流式聊天接口（实时工具调用可见）
  - 监控规则 CRUD
  - 知识库管理（上传 / 列表 / 删除）

启动: uvicorn api.server:app --reload --port 8001
"""

import os
import re
import json
import asyncio
import shutil
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from src.agent.graph import build_graph
from src.config.settings import TAVILY_API_KEY, CHART_DIR, DATA_DIR
from src.monitor.rules import add_rule, list_rules, remove_rule
from src.rag.vector_store import list_sources, delete_by_source, get_db_stats
from src.rag.ingest import ingest_file


TOOL_DISPLAY = {
    'get_stock_price':              ('📈', '查询实时行情'),
    'get_multi_stock_prices':       ('📊', '批量对比行情'),
    'get_stock_history':            ('📉', '获取历史数据'),
    'get_technical_indicators':     ('📐', '计算技术指标'),
    'get_financial_data':           ('💰', '查询财务数据'),
    'generate_kline_chart':         ('🕯️', '生成K线图'),
    'search_web':                   ('🌐', '联网搜索'),
    'search_stock_news':            ('📰', '搜索个股新闻'),
    'search_investment_knowledge':  ('📚', '检索知识库'),
    'get_knowledge_db_info':        ('📚', '查看知识库状态'),
    'add_stock_monitor':            ('🔔', '添加监控规则'),
    'list_stock_monitors':          ('📋', '查看监控规则'),
    'remove_stock_monitor':         ('🗑️', '删除监控规则'),
    # Tavily MCP tools
    'tavily_search':                ('🌐', '联网搜索 (MCP)'),
    'tavily_extract':               ('📄', '网页内容提取 (MCP)'),
    'tavily_crawl':                 ('🕷️', '网站爬取 (MCP)'),
    'tavily_map':                   ('🗺️', '网站结构分析 (MCP)'),
}


def _format_tool_input(name: str, args: dict) -> str:
    """生成工具输入的简短摘要。"""
    if name in ('get_stock_price', 'get_financial_data', 'get_technical_indicators'):
        return args.get('symbol', '')
    if name == 'get_multi_stock_prices':
        return args.get('symbols', '')
    if name == 'generate_kline_chart':
        s = args.get('symbol', '')
        d = args.get('days', 60)
        return f"{s}（{d}天）"
    if name in ('search_web', 'search_stock_news', 'search_investment_knowledge',
                 'tavily_search', 'tavily_extract', 'tavily_crawl', 'tavily_map'):
        return args.get('query', '') or args.get('stock_name', '') or args.get('url', '') or args.get('urls', [''])[0] if isinstance(args.get('urls'), list) else args.get('query', '')
    if name == 'get_stock_history':
        s = args.get('symbol', '')
        d = args.get('days', 30)
        return f"{s}（{d}天）"
    return json.dumps(args, ensure_ascii=False)[:60] if args else ''


def _flatten_tool_content(content) -> str:
    """将 ToolMessage 的 content 统一转为字符串。支持 MCP 返回的 list 格式。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(block.get("text", block.get("content", str(block))))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return str(content)


def _extract_references(tool_name: str, content: str) -> list[dict]:
    """从工具返回内容中提取引用来源。"""
    refs = []
    search_tools = ('search_web', 'search_stock_news', 'tavily_search', 'tavily_extract', 'tavily_crawl')
    # MCP 可能使用 tavily-search 等带连字符的名称
    is_search_tool = tool_name in search_tools or (
        tool_name and ('search' in tool_name.lower() or 'tavily' in tool_name.lower())
    )
    if is_search_tool:
        # 格式1: 【N】https://...
        for m in re.finditer(r'【\d+】(https?://\S+)', content):
            url = m.group(1).rstrip(')')
            domain = re.sub(r'^https?://(www\.)?', '', url).split('/')[0]
            refs.append({'url': url, 'title': domain})
        # 格式2: "url": "https://..." 或 url: "https://..."
        for m in re.finditer(r'"?url"?\s*[:=]\s*"?(https?://[^\s"\')\]]+)"?', content):
            url = m.group(1).rstrip('"\'.,;')
            domain = re.sub(r'^https?://(www\.)?', '', url).split('/')[0]
            if url not in [r['url'] for r in refs]:
                refs.append({'url': url, 'title': domain})
        # 格式3: 兜底 - 提取所有 http(s) 链接（避免误匹配代码片段，仅对搜索类工具）
        if not refs:
            for m in re.finditer(r'https?://[^\s\'"<>)\]]+', content):
                url = m.group(0).rstrip('.,;)\'\"')
                if len(url) > 20 and url not in [r['url'] for r in refs]:
                    domain = re.sub(r'^https?://(www\.)?', '', url).split('/')[0]
                    refs.append({'url': url, 'title': domain})
    elif tool_name == 'search_investment_knowledge':
        # 新格式 [Source | 类型] 或旧格式 来源: xxx
        for m in re.finditer(r'\[([^|\]]+)\s*\|[^\]]*\]', content):
            source = m.group(1).strip()
            if source and source not in [r['title'] for r in refs]:
                refs.append({'url': '', 'title': f'📄 {source}'})
        for m in re.finditer(r'来源:\s*(\S+)', content):
            source = m.group(1)
            if source not in [r['title'] for r in refs]:
                refs.append({'url': '', 'title': f'📄 {source}'})
    return refs


agent = None
_mcp_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent, _mcp_client

    mcp_tools = []

    if TAVILY_API_KEY:
        try:
            from langchain_mcp_adapters.client import MultiServerMCPClient
            _mcp_client = MultiServerMCPClient({
                "tavily": {
                    "url": f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}",
                    "transport": "streamable_http",
                }
            })
            # langchain-mcp-adapters 0.1.0+ 不再支持 context manager，直接调用 get_tools
            mcp_tools = await _mcp_client.get_tools()
            print(f"[MCP Client] Tavily MCP connected — {len(mcp_tools)} tools: {[t.name for t in mcp_tools]}")
        except Exception as e:
            print(f"[MCP Client] Tavily MCP failed: {e} — falling back to direct SDK")
            _mcp_client = None

    agent = build_graph(mcp_tools=mcp_tools or None)
    yield

    # 新版本无需显式关闭，_mcp_client 仅保留供后续扩展


app = FastAPI(title="A股分析Agent API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

sessions: dict[str, list] = {}


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class MonitorRequest(BaseModel):
    symbol: str
    condition: str
    threshold: float
    description: str = ""


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """SSE 流式聊天，实时推送工具调用步骤和引用。"""
    if req.session_id not in sessions:
        sessions[req.session_id] = []

    messages = sessions[req.session_id]
    messages.append(HumanMessage(content=req.message))

    async def event_stream():
        all_references: list[dict] = []
        full_chunks: list[str] = []
        emitted_tools: set[str] = set()

        # 使用 astream 以支持 MCP 等异步工具（sync stream 会报 StructuredTool does not support sync invocation）
        async for msg, metadata in agent.astream(
            {"messages": messages},
            stream_mode="messages",
        ):
            node = metadata.get("langgraph_node", "")

            if isinstance(msg, AIMessage) and msg.tool_calls and node == "chatbot":
                for tc in msg.tool_calls:
                    name = tc.get('name', '')
                    if not name:
                        continue
                    tc_id = tc.get('id', name)
                    if tc_id in emitted_tools:
                        continue
                    emitted_tools.add(tc_id)
                    icon, display = TOOL_DISPLAY.get(name, ('🔧', name))
                    yield f"data: {json.dumps({'type': 'tool_start', 'id': tc_id, 'name': name, 'icon': icon, 'displayName': display, 'inputSummary': _format_tool_input(name, tc.get('args', {}))}, ensure_ascii=False)}\n\n"

            elif isinstance(msg, ToolMessage) and node == "tools":
                content_str = _flatten_tool_content(msg.content)
                refs = _extract_references(msg.name or '', content_str)
                all_references.extend(refs)
                yield f"data: {json.dumps({'type': 'tool_end', 'id': msg.tool_call_id or '', 'name': msg.name or ''}, ensure_ascii=False)}\n\n"

            elif (
                isinstance(msg, AIMessage)
                and not msg.tool_calls
                and msg.content
                and node == "chatbot"
            ):
                full_chunks.append(msg.content)
                yield f"data: {json.dumps({'type': 'token', 'content': msg.content}, ensure_ascii=False)}\n\n"

        full_content = "".join(full_chunks)

        images = []
        png_paths = re.findall(r'[\w/._-]+\.png', full_content)
        for p in png_paths:
            p = p.strip('`').strip()
            filename = os.path.basename(p)
            chart_path = CHART_DIR / filename
            if chart_path.exists():
                images.append(f"/api/charts/{filename}")

        seen_urls = set()
        unique_refs = []
        for r in all_references:
            key = r['url'] or r['title']
            if key not in seen_urls:
                seen_urls.add(key)
                unique_refs.append(r)

        messages.append(AIMessage(content=full_content))
        done_event = {'type': 'done', 'images': images, 'references': unique_refs}
        yield f"data: {json.dumps(done_event, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/charts/{filename}")
async def get_chart(filename: str):
    """获取生成的 K 线图。"""
    filepath = CHART_DIR / filename
    if filepath.exists():
        return FileResponse(str(filepath), media_type="image/png")
    return {"error": "not found"}


@app.get("/api/monitors")
async def get_monitors():
    return list_rules()


@app.post("/api/monitors")
async def create_monitor(req: MonitorRequest):
    rule = add_rule(req.symbol, req.condition, req.threshold, req.description)
    return rule


@app.delete("/api/monitors/{rule_id}")
async def delete_monitor(rule_id: int):
    ok = remove_rule(rule_id)
    return {"success": ok}


@app.get("/api/sessions/{session_id}/clear")
async def clear_session(session_id: str):
    sessions.pop(session_id, None)
    return {"success": True}


UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/api/knowledge")
async def get_knowledge():
    sources = list_sources()
    stats = get_db_stats()
    return {"sources": sources, "total_chunks": stats["total_documents"]}


@app.post("/api/knowledge/upload")
async def upload_knowledge(file: UploadFile = File(...)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in (".pdf", ".txt", ".md"):
        return {"error": f"不支持的文件格式: {ext}（支持 .pdf, .txt, .md）"}

    save_path = UPLOAD_DIR / (file.filename or "upload.txt")
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    loop = asyncio.get_event_loop()
    try:
        added = await loop.run_in_executor(None, ingest_file, save_path)
    except Exception as e:
        return {"error": str(e)}

    return {"success": True, "filename": file.filename, "chunks_added": added}


@app.delete("/api/knowledge/{source_name:path}")
async def delete_knowledge(source_name: str):
    deleted = delete_by_source(source_name)
    return {"success": True, "deleted_chunks": deleted}
