---
name: stock-monitor
description: Manage stock monitoring and alert rules through conversation. Use when the user asks to set up price alerts, monitor stocks, view monitoring list, or delete monitoring rules.
---

# 股票监控管理

通过自然语言对话管理股票监控告警规则。

## Tools

| Tool | 功能 | 参数 |
|------|------|------|
| `add_stock_monitor` | 添加监控规则 | `symbol`, `condition`, `threshold`, `description` |
| `list_stock_monitors` | 查看所有规则 | 无参数 |
| `remove_stock_monitor` | 删除指定规则 | `rule_id` |

## 支持的条件类型

| condition | 含义 | 示例 |
|-----------|------|------|
| `price_above` | 价格高于阈值 | 突破 100 元 |
| `price_below` | 价格低于阈值 | 跌破 90 元 |
| `change_pct_above` | 涨幅超过百分比 | 涨超 5% |
| `change_pct_below` | 跌幅超过百分比 | 跌超 -5% |

## 配套系统

规则存储在 `data/monitor_rules.json`。后台监控服务：

```bash
python -m src.monitor.scheduler           # 启动持续监控
python -m src.monitor.scheduler --morning  # 盘前摘要
```

## 脚本

实现文件：[scripts/monitor_skill.py](scripts/monitor_skill.py)

导出：`MONITOR_TOOLS` 列表
