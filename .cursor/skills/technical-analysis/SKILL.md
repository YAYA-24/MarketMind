---
name: technical-analysis
description: Calculate stock technical indicators including MA, MACD, KDJ, RSI, and Bollinger Bands, with signal analysis. Use when the user asks about technical analysis, moving averages, overbought/oversold signals, or trend analysis.
---

# 技术指标分析

基于历史 K 线计算常用技术指标并给出信号解读。

## Tools

| Tool | 功能 | 参数 |
|------|------|------|
| `get_technical_indicators` | 计算 MA/MACD/KDJ/RSI/布林带 + 信号分析 | `symbol`: 6 位代码 |

## 指标说明

- **MA** (5/10/20/60)：多头排列 → 趋势偏多，空头排列 → 趋势偏空
- **MACD**：金叉做多，死叉做空
- **KDJ**：K/D > 80 超买，< 20 超卖
- **RSI** (6/12/24)：> 80 过热，< 20 超跌
- **布林带**：突破上轨可能超买，跌破下轨可能超卖

## 依赖

- `pandas_ta`：技术指标计算
- `akshare`：获取 120 天历史数据

## 脚本

实现文件：[scripts/technical.py](scripts/technical.py)

导出：`TECHNICAL_TOOLS` 列表
