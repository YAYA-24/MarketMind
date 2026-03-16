# MarketMind — A 股智能分析助手

> 基于 LangGraph + DeepSeek 构建的 AI Agent，覆盖行情查询、技术分析、财报解读、联网搜索、知识库检索、K 线图生成和股票监控告警，配有 React Web 界面和 MCP 协议接入。

这是一个为个人日常看盘和学习 AI Agent 技术而开发的项目，后续会根据实际使用持续迭代。

---

## 功能一览

| 功能 | 说明 | 示例 |
|------|------|------|
| 实时行情 | 查询 A 股实时价格、涨跌幅、成交量 | "查一下茅台现在的股价" |
| 多股对比 | 同时查询多只股票横向对比 | "对比茅台、五粮液和平安银行" |
| 历史数据 | 获取日/周/月级别历史 K 线 | "比亚迪最近 30 天的走势" |
| 技术指标 | MA / MACD / KDJ / RSI / 布林带 + 信号解读 | "分析比亚迪的技术指标" |
| 财务数据 | PE / ROE / 营收 / 利润 / 资产负债率 | "查一下宁德时代的财务数据" |
| K 线图 | 蜡烛图 + 均线 + 成交量，前端内嵌展示 | "帮我画一下比亚迪的K线图" |
| 联网搜索 | 实时财经新闻、公司公告、市场动态 | "比亚迪最近有什么消息" |
| 知识库 (RAG) | 导入投资书籍 / 论文，语义检索 | "什么是安全边际" |
| 监控告警 | 价格 / 涨跌幅条件监控 | "比亚迪跌破 90 元就提醒我" |

## 亮点

- **真正的 Agent** — 基于 LangGraph 的 ReAct 循环，LLM 自主决策调用哪些工具、以什么顺序调用
- **实时流式回答** — 前端实时显示工具调用步骤（哪个工具在跑、输入是什么），回答逐字流出
- **引用来源** — 联网搜索结果自动提取 URL；知识库检索自动标注文件来源
- **Web UI** — React + Tailwind 暗色主题，Markdown 渲染、K 线图内嵌显示、点击放大保存
- **Cursor MCP** — 通过 MCP 协议在 Cursor IDE 中直接调用全部分析能力
- **Cursor Agent Skills** — 每个工具模块配有 `SKILL.md`，让 Cursor 理解项目的 Skill 体系

---

## 快速开始

### 1. 克隆 & 安装

```bash
git clone https://github.com/<your-username>/marketmind.git
cd marketmind
pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
cp .env.example .env
```

编辑 `.env`，填入两个 Key：

| Key | 获取方式 | 费用 |
|-----|---------|------|
| `DEEPSEEK_API_KEY` | [platform.deepseek.com](https://platform.deepseek.com) | 充值 10 元够用很久 |
| `TAVILY_API_KEY` | [tavily.com](https://tavily.com) | 免费 1000 次/月 |

### 3. 启动

**方式一：Web 界面（推荐）**

```bash
# 终端 1 — 后端
uvicorn api.server:app --reload --port 8001

# 终端 2 — 前端
cd web && npm install && npm run dev
```

打开 `http://localhost:5173` 即可使用。

**方式二：命令行**

```bash
python main.py
```

---

## 进阶用法

### 导入投资书籍到知识库

支持 PDF / TXT / MD 格式。可以通过 Web 界面侧栏的「知识库」面板上传，也可以用命令行：

```bash
python -m src.rag.ingest path/to/book.pdf     # 单个文件
python -m src.rag.ingest data/books/           # 整个目录
python -m src.rag.ingest --stats               # 查看状态
```

### 股票监控

在 Web 界面侧栏的「监控面板」添加规则，或在对话中直接说：

```
帮我监控比亚迪，跌破 90 元提醒我
```

启动后台监控定时检查（交易时段自动运行）：

```bash
python -m src.monitor.scheduler
```

### 在 Cursor 中使用 (MCP Server，可选)

项目附带了一个 MCP Server（`mcp_server/server.py`），可以把全部分析工具暴露给 Cursor / Claude Desktop 等支持 MCP 协议的客户端。这是一个**可选模块**，不影响 Web 界面和 CLI 的正常使用。

启用方式：重启 Cursor 后在 Settings → MCP 确认 `a-stock-analyzer` 已连接，即可在 Cursor 对话中直接调用全部工具。

---

## 项目结构

```
marketmind/
├── main.py                          # CLI 对话入口
├── requirements.txt
├── .env.example
│
├── api/                             # FastAPI 后端
│   └── server.py                    #   SSE 流式聊天 / 监控 CRUD / 知识库管理
│
├── web/                             # React + Vite 前端
│   └── src/
│       ├── App.tsx
│       └── components/
│           ├── ChatWindow.tsx       #   聊天窗口 (Markdown / 工具步骤 / 引用)
│           ├── Sidebar.tsx          #   侧栏 (标签页切换)
│           ├── MonitorPanel.tsx     #   监控规则管理
│           └── KnowledgePanel.tsx   #   知识库文件管理
│
├── skills/                          # Skill 主目录（项目本体），Cursor 通过符号链接共用
│   ├── stock-data/
│   │   ├── SKILL.md
│   │   └── scripts/stock_data.py
│   ├── technical-analysis/
│   ├── financial-data/
│   ├── kline-chart/
│   ├── web-search/
│   ├── knowledge-rag/
│   ├── stock-monitor/
│   └── ui-ux-designer/
│
├── src/
│   ├── agent/
│   │   └── graph.py                 # LangGraph Agent 核心 (ReAct 循环)
│   ├── config/
│   │   └── settings.py              # 环境变量 & 系统提示词 & 路径常量
│   ├── sina.py                      # 新浪财经 API 公共模块（行情/K线解析）
│   ├── utils/                       # 通用工具
│   │   └── retry.py                 # 指数退避重试（akshare 等）
│   ├── skills/                      # 工具桥接层，动态加载 skills/*/scripts/
│   │   ├── stock_data.py            #   → skills/stock-data/scripts/stock_data.py
│   │   ├── technical.py             #   → skills/technical-analysis/scripts/technical.py
│   │   ├── financial.py             #   → skills/financial-data/scripts/financial.py
│   │   ├── kline_chart.py           #   → skills/kline-chart/scripts/kline_chart.py
│   │   ├── web_search.py            #   → skills/web-search/scripts/web_search.py
│   │   ├── knowledge_rag.py         #   → skills/knowledge-rag/scripts/knowledge_rag.py
│   │   └── monitor_skill.py         #   → skills/stock-monitor/scripts/monitor_skill.py
│   ├── rag/                         # RAG 知识库
│   │   ├── vector_store.py          #   ChromaDB 向量存储
│   │   └── ingest.py                #   文档导入 (PDF/TXT/MD)
│   └── monitor/                     # 监控系统
│       ├── rules.py                 #   规则引擎
│       └── scheduler.py             #   定时任务
│
├── .cursor/
│   ├── mcp.json                     # Cursor MCP 配置 (cwd 使用 ${workspaceFolder})
│   └── skills/                      # 符号链接 → ../skills/（Cursor 从此处发现 Skill）
│
├── mcp_server/                      # [可选] MCP Server
│   └── server.py                    #   复用 src.skills，供 Cursor/Claude Desktop 调用
│
└── data/
    └── books/                       # 投资书籍 (用户自行放入)
```

## 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| Agent 编排 | LangGraph | ReAct 状态图、工具路由 |
| 大模型 | DeepSeek-V3 | 推理 & Function Calling |
| 工具定义 | LangChain `@tool` | 自动生成 JSON Schema |
| 数据源 | 新浪财经 API / akshare | 实时行情 / 历史数据 / 财务 |
| 联网搜索 | Tavily MCP | AI Agent 专用搜索（通过 MCP 协议接入） |
| 向量数据库 | ChromaDB | RAG 知识存储 & 语义检索 |
| 技术指标 | pandas_ta | MA / MACD / KDJ / RSI / BOLL |
| K 线图 | mplfinance + matplotlib | 蜡烛图 + 均线 + 成交量 |
| Web 后端 | FastAPI + SSE | 流式聊天 / 文件上传 / CRUD |
| Web 前端 | React + Vite + Tailwind | 暗色主题 / Markdown / 图片灯箱 |
| MCP Server | mcp Python SDK | [可选] 供 Cursor/Claude Desktop 调用 |
| MCP Client | langchain-mcp-adapters | 接入外部 MCP 服务（Tavily） |

---

## Roadmap

- [ ] 更强的中文 Embedding 模型（BGE 替代 MiniLM）
- [ ] LangGraph Checkpoint 对话持久化
- [ ] 异步工具调用提升并发性能
- [ ] 更多数据源（港股、美股、基金）
- [ ] 移动端适配

## 免责声明

本项目仅用于个人学习和日常辅助，所有分析结果仅供参考，不构成任何投资建议。投资有风险，入市需谨慎。
