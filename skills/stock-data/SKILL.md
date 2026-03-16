---
name: stock-data
description: Query A-share stock real-time prices, historical K-line data, and multi-stock comparison. Use when the user asks about stock prices, market quotes, historical trends, or wants to compare multiple stocks.
---

# A 股行情数据

查询 A 股实时行情和历史 K 线数据。

## Tools

| Tool | 功能 | 参数 |
|------|------|------|
| `get_stock_price` | 单只股票实时行情 | `symbol`: 6 位代码，如 `"600519"` |
| `get_multi_stock_prices` | 多股同时对比 | `symbols`: 逗号分隔，如 `"600519,000001"` |
| `get_stock_history` | 历史 K 线 | `symbol`, `period`(daily/weekly/monthly), `days` |

## 数据源策略

- **实时行情** → 新浪财经 API（快速稳定，GBK 编码）
- **历史 K 线** → 新浪财经 API（quotes.sina.cn JSONP 接口）

新浪 API 返回格式：`var hq_str_shXXXXXX="名称,今开,昨收,最新价,...";`

## 脚本

实现文件：[scripts/stock_data.py](scripts/stock_data.py)

导出：`ALL_TOOLS` 列表
