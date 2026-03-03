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
import queue
import shutil
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from src.agent.graph import build_graph
from src.config.settings import TAVILY_API_KEY
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


def _extract_references(tool_name: str, content: str) -> list[dict]:
    """从工具返回内容中提取引用来源。"""
    refs = []
    if tool_name in ('search_web', 'search_stock_news', 'tavily_search'):
        for m in re.finditer(r'【\d+】(https?://\S+)', content):
            url = m.group(1)
            domain = re.sub(r'^https?://(www\.)?', '', url).split('/')[0]
            refs.append({'url': url, 'title': domain})
        for m in re.finditer(r'"?url"?\s*[:=]\s*"?(https?://\S+?)"', content):
            url = m.group(1).rstrip('",')
            domain = re.sub(r'^https?://(www\.)?', '', url).split('/')[0]
            if url not in [r['url'] for r in refs]:
                refs.append({'url': url, 'title': domain})
    elif tool_name == 'search_investment_knowledge':
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
            await _mcp_client.__aenter__()
            mcp_tools = _mcp_client.get_tools()
            print(f"[MCP Client] Tavily MCP connected — {len(mcp_tools)} tools: {[t.name for t in mcp_tools]}")
        except Exception as e:
            print(f"[MCP Client] Tavily MCP failed: {e} — falling back to direct SDK")
            _mcp_client = None

    agent = build_graph(mcp_tools=mcp_tools or None)
    yield

    if _mcp_client:
        try:
            await _mcp_client.__aexit__(None, None, None)
        except Exception:
            pass


app = FastAPI(title="A股分析Agent API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

CHARTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'charts'))

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
        q: queue.Queue = queue.Queue()
        loop = asyncio.get_event_loop()

        def run_sync():
            all_references: list[dict] = []
            full_chunks: list[str] = []
            emitted_tools: set[str] = set()

            for msg, metadata in agent.stream(
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
                        q.put({
                            'type': 'tool_start',
                            'id': tc_id,
                            'name': name,
                            'icon': icon,
                            'displayName': display,
                            'inputSummary': _format_tool_input(name, tc.get('args', {})),
                        })

                elif isinstance(msg, ToolMessage) and node == "tools":
                    content_str = msg.content if isinstance(msg.content, str) else str(msg.content)
                    refs = _extract_references(msg.name or '', content_str)
                    all_references.extend(refs)
                    q.put({
                        'type': 'tool_end',
                        'id': msg.tool_call_id or '',
                        'name': msg.name or '',
                    })

                elif (
                    isinstance(msg, AIMessage)
                    and not msg.tool_calls
                    and msg.content
                    and node == "chatbot"
                ):
                    full_chunks.append(msg.content)
                    q.put({
                        'type': 'token',
                        'content': msg.content,
                    })

            full_content = "".join(full_chunks)

            images = []
            png_paths = re.findall(r'[\w/._-]+\.png', full_content)
            for p in png_paths:
                p = p.strip('`').strip()
                if os.path.exists(p):
                    filename = os.path.basename(p)
                    images.append(f"/api/charts/{filename}")

            seen_urls = set()
            unique_refs = []
            for r in all_references:
                key = r['url'] or r['title']
                if key not in seen_urls:
                    seen_urls.add(key)
                    unique_refs.append(r)

            q.put({
                'type': 'done',
                'images': images,
                'references': unique_refs,
                'full_content': full_content,
            })

        loop.run_in_executor(None, run_sync)

        while True:
            try:
                event = q.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.05)
                continue

            if event.get('type') == 'done':
                full_content = event.pop('full_content', '')
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                messages.append(AIMessage(content=full_content))
                break

            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/charts/{filename}")
async def get_chart(filename: str):
    """获取生成的 K 线图。"""
    filepath = os.path.join(CHARTS_DIR, filename)
    if os.path.exists(filepath):
        return FileResponse(filepath, media_type="image/png")
    for root, dirs, files in os.walk(os.path.join(os.path.dirname(__file__), '..')):
        if filename in files:
            return FileResponse(os.path.join(root, filename), media_type="image/png")
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


UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'uploads'))
os.makedirs(UPLOAD_DIR, exist_ok=True)


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

    save_path = os.path.join(UPLOAD_DIR, file.filename or "upload.txt")
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
