---
name: web-search
description: Search the web for latest financial news, market dynamics, and company announcements using Tavily API. Use when the user asks about recent news, latest events, current market conditions, or any real-time information.
---

# 联网搜索

通过 Tavily 搜索 API 获取最新财经新闻和市场动态。

## Tools

| Tool | 功能 | 参数 |
|------|------|------|
| `search_web` | 通用财经搜索 | `query`: 搜索关键词 |
| `search_stock_news` | 指定股票的新闻搜索 | `stock_name`: 股票名称或代码 |

## 设计决策

实时新闻使用联网搜索而非 RAG，因为：
- 新闻时效性极强（分钟级），不适合先入库再检索
- Tavily 返回结构化文本，可直接喂给 LLM
- 免费额度 1000 次/月足够日常使用

## 配置

需要在 `.env` 中设置 `TAVILY_API_KEY`（[tavily.com](https://tavily.com) 注册获取）。

## 脚本

实现文件：[scripts/web_search.py](scripts/web_search.py)

导出：`WEB_SEARCH_TOOLS` 列表
