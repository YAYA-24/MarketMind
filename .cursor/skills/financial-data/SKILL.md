---
name: financial-data
description: Query A-share company financial data including PE, PB, ROE, revenue growth, profit growth, and debt ratio. Use when the user asks about fundamentals, valuation, earnings, or financial health of a listed company.
---

# 财务数据查询

查询上市公司核心财务指标，支持估值和基本面分析。

## Tools

| Tool | 功能 | 参数 |
|------|------|------|
| `get_financial_data` | 市值/PE/ROE/营收/利润增速/资产负债率 | `symbol`: 6 位代码 |

## 返回指标

- **估值**：总市值、流通市值
- **盈利能力**：EPS、BPS、ROE、毛利率、净利率
- **成长性**：营收同比增长、净利润同比增长
- **财务健康**：资产负债率、每股经营现金流
- **参考**：格雷厄姆公式（合理价格 = √(22.5 × EPS × BPS)）

## 依赖

- `akshare`：个股基本信息 + 财务摘要（东方财富数据源）

## 脚本

实现文件：[scripts/financial.py](scripts/financial.py)

导出：`FINANCIAL_TOOLS` 列表
