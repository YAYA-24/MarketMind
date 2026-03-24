# MarketMind 项目总结

## 一、项目介绍

**MarketMind** 是一个基于 LangGraph + DeepSeek 构建的 A 股智能分析助手，面向个人日常看盘和 AI Agent 技术学习。

核心定位：**真正的 AI Agent** —— LLM 自主决策调用哪些工具、以什么顺序调用，而非预编程流程。用户用自然语言提问（如「帮我分析一下茅台」），Agent 会自主决定查行情、看技术指标、查财务、搜新闻、检索知识库，并综合给出分析报告。

---

## 二、功能一览

| 功能 | 说明 | 示例 |
|------|------|------|
| 实时行情 | A 股实时价格、涨跌幅、成交量 | "查一下茅台现在的股价" |
| 多股对比 | 多只股票横向对比 | "对比茅台、五粮液和平安银行" |
| 历史数据 | 日/周/月 K 线 | "比亚迪最近 30 天的走势" |
| 技术指标 | MA / MACD / KDJ / RSI / 布林带 + 信号解读 | "分析比亚迪的技术指标" |
| 财务数据 | PE / ROE / 营收 / 利润 / 资产负债率 | "查一下宁德时代的财务数据" |
| K 线图 | 蜡烛图 + 均线 + 成交量，前端内嵌 | "帮我画一下比亚迪的K线图" |
| 联网搜索 | 实时财经新闻、公司公告 | "比亚迪最近有什么消息" |
| 知识库 (RAG) | 导入投资书籍/论文，语义检索 | "什么是安全边际" |
| 监控告警 | 价格/涨跌幅条件监控 | "比亚迪跌破 90 元就提醒我" |

---

## 三、技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| Agent 编排 | LangGraph | ReAct 状态图、工具路由 |
| 大模型 | DeepSeek-V3 | 推理 & Function Calling |
| 工具定义 | LangChain `@tool` | 自动生成 JSON Schema |
| 数据源 | 新浪财经 API / akshare | 实时行情 / 历史数据 / 财务 |
| 联网搜索 | Tavily MCP | AI Agent 专用搜索 |
| 向量数据库 | ChromaDB + BGE + BM25 | RAG 混合检索 + Rerank |
| 技术指标 | pandas_ta | MA / MACD / KDJ / RSI / BOLL |
| K 线图 | mplfinance + matplotlib | 蜡烛图 + 均线 + 成交量 |
| Web | FastAPI + React + Vite + Tailwind | 流式聊天 / 暗色主题 |
| MCP | mcp Python SDK | 供 Cursor/Claude Desktop 调用 |

---

## 四、项目结构（核心模块）

```
marketmind/
├── main.py                    # CLI 入口
├── api/server.py             # FastAPI 后端（SSE 流式、监控 CRUD、知识库管理）
├── web/                      # React 前端
├── src/
│   ├── agent/graph.py        # LangGraph Agent 核心
│   ├── sina.py               # 新浪财经 API 公共模块
│   ├── utils/retry.py        # 指数退避重试
│   ├── skills/               # 工具桥接层
│   ├── rag/                  # RAG 全链路
│   │   ├── vector_store.py   # 混合检索 + Rerank 入口
│   │   ├── embedding.py     # BGE + Query Expansion + RRF
│   │   ├── bm25_index.py     # BM25 关键词检索
│   │   ├── reranker.py       # Cross-Encoder Rerank
│   │   ├── context_builder.py # 上下文构建
│   │   ├── chunker.py        # 结构感知切分
│   │   └── ingest.py        # 文档导入
│   └── monitor/              # 监控规则 + 定时任务
├── skills/                   # Skill 主目录（SKILL.md + scripts）
├── mcp_server/               # MCP Server（可选）
├── eval/                     # RAG 评估
│   ├── queries.json
│   ├── ground_truth.json
│   └── evaluation.py
└── data/                     # 运行时数据
```

---

## 五、一步步优化历程

### 1. 项目结构与路径统一

- **问题**：路径硬编码、MCP 配置分散
- **优化**：`src/config/settings.py` 定义 `PROJECT_ROOT`、`DATA_DIR`、`CHART_DIR`；`.cursor/mcp.json` 使用 `cwd: "${workspaceFolder}"`、`envFile: ".env"`
- **结果**：配置集中、跨环境一致

### 2. Skill 与 MCP 体系统一

- **问题**：Skill 散落在 `.cursor/skills/`，项目本体与 Cursor 各用一套
- **优化**：Skill 主目录迁移到 `skills/`，`.cursor/skills/` 改为符号链接；`get_skill_descriptions()` 从 SKILL.md 加载并注入 Agent
- **结果**：项目本体与 Cursor 共用同一套 Skill 定义

### 3. 代码去重与公共模块

- **问题**：新浪 API、重试逻辑在多个 Skill 中重复实现
- **优化**：`src/sina.py` 集中新浪行情/K线解析；`src/utils/retry.py` 通用重试；MCP Server 通过 `_invoke_skill()` 统一调用 `src.skills`
- **结果**：单一数据源、易维护

### 4. RAG 分块策略优化

- **问题**：固定 500 字按字符切分，语义断裂、碎片化
- **优化**：`src/rag/chunker.py` 结构感知切分
  - 按标题（##、第X章、一、二、1. 2. 3.）
  - 表格单独保留
  - 双层 chunk：小块（~200 tokens）召回，大块（~800 tokens）生成
  - 文档类型策略：book/report/news
- **结果**：召回更连贯，生成上下文更完整

### 5. Embedding 优化

- **问题**：ChromaDB 默认 all-MiniLM-L6-v2 偏英文，中文效果一般
- **优化**：`src/rag/embedding.py` 使用 BAAI/bge-small-zh-v1.5；Query Expansion（金融术语同义 + 可选 LLM 扩写）；多路检索 RRF 融合
- **结果**：中文检索质量提升

### 6. 混合检索（Dense + BM25）

- **问题**：纯向量检索对「ROE」「净利润同比」「现金流」等关键词不敏感
- **优化**：`src/rag/bm25_index.py` 引入 BM25；Dense top 50 + BM25 top 50 → RRF 融合
- **结果**：关键词召回显著提升

### 7. Cross-Encoder Rerank

- **问题**：没有 Rerank 的 RAG 是半成品
- **优化**：`src/rag/reranker.py` 使用 BGE-reranker-base；Top 20 → Rerank → Top 5
- **结果**：Top-K 精度明显提升

### 8. 上下文构建优化

- **问题**：简单 `"\n".join(docs)` 导致重复、无来源、token 超限
- **优化**：`src/rag/context_builder.py` 按相关度排序、去重、控制 token budget、标注 `[Source | 时间/类型]`
- **结果**：LLM 幻觉减少，来源可追溯

### 9. 评估系统

- **问题**：无法量化改进效果
- **优化**：`eval/` 自动评估 Recall@5、Precision@5、MRR、生成正确率
- **结果**：每次优化后可对比指标，验证是否进步

---

## 六、RAG 完整管线（当前）

```
离线：
  文档 → 结构感知切分(Chunker) → BGE 嵌入 → ChromaDB

在线：
  用户 query → Query Expansion(可选)
       ↓
  Dense top 50  ←→  BM25 top 50  （混合检索）
       ↓              ↓
       └── RRF 融合 ──┘
             ↓
  Top 20 → Cross-Encoder Rerank
             ↓
  Top 5 → 上下文构建（去重、token budget、来源标注）
             ↓
  注入 Prompt → LLM 生成
```

---

## 七、快速开始

```bash
# 安装
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填入 DEEPSEEK_API_KEY、TAVILY_API_KEY

# 启动 Web
uvicorn api.server:app --reload --port 8001
cd web && npm install && npm run dev

# 导入知识库
python -m src.rag.ingest path/to/book.pdf

# 运行评估
python -m eval.evaluation
```

---

## 八、免责声明

本项目仅用于个人学习和日常辅助，所有分析结果仅供参考，不构成任何投资建议。投资有风险，入市需谨慎。
