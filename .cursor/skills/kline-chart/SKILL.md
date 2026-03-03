---
name: kline-chart
description: Generate candlestick (K-line) chart images with volume and moving averages for A-share stocks. Use when the user asks to draw, plot, or visualize a stock's K-line chart or price trend.
---

# K 线图生成

生成专业的 K 线蜡烛图并保存为 PNG 图片。

## Tools

| Tool | 功能 | 参数 |
|------|------|------|
| `generate_kline_chart` | 生成 K 线图（蜡烛图 + 成交量 + MA 均线） | `symbol`, `days`(默认 60) |

## 图表内容

- 日 K 线蜡烛图（红涨绿跌，A 股配色）
- 成交量柱状图
- MA5 / MA10 / MA20 移动平均线
- 输出路径：`./data/charts/{symbol}_kline.png`（150 DPI）

## 依赖

- `mplfinance`：专业金融图表库
- `akshare`：历史 K 线数据

## 脚本

实现文件：[scripts/kline_chart.py](scripts/kline_chart.py)

导出：`KLINE_TOOLS` 列表
