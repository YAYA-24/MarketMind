"""
监控规则引擎。

管理用户设置的股票监控规则，支持：
- 价格上穿/下破阈值
- 涨跌幅超过阈值
- 成交量异常放大

规则以 JSON 文件持久化存储，简单可靠。
"""

import json
import os
from datetime import datetime

RULES_FILE = "./data/monitor_rules.json"


def _load_rules() -> list[dict]:
    if not os.path.exists(RULES_FILE):
        return []
    with open(RULES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_rules(rules: list[dict]):
    os.makedirs(os.path.dirname(RULES_FILE), exist_ok=True)
    with open(RULES_FILE, "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)


def add_rule(
    symbol: str,
    condition: str,
    threshold: float,
    description: str = "",
) -> dict:
    """
    添加一条监控规则。

    Args:
        symbol: 股票代码
        condition: 条件类型，可选：
            "price_above" - 价格高于阈值
            "price_below" - 价格低于阈值
            "change_pct_above" - 涨幅超过阈值（%）
            "change_pct_below" - 跌幅超过阈值（%，用负数）
            "volume_ratio_above" - 量比超过阈值
        threshold: 阈值
        description: 规则描述
    """
    rules = _load_rules()
    rule = {
        "id": len(rules) + 1,
        "symbol": symbol,
        "condition": condition,
        "threshold": threshold,
        "description": description or f"{symbol} {condition} {threshold}",
        "enabled": True,
        "created_at": datetime.now().isoformat(),
        "last_triggered": None,
    }
    rules.append(rule)
    _save_rules(rules)
    return rule


def list_rules() -> list[dict]:
    return _load_rules()


def remove_rule(rule_id: int) -> bool:
    rules = _load_rules()
    new_rules = [r for r in rules if r["id"] != rule_id]
    if len(new_rules) == len(rules):
        return False
    _save_rules(new_rules)
    return True


def check_rules(stock_data: dict) -> list[dict]:
    """
    检查所有规则是否被触发。

    Args:
        stock_data: 股票实时数据，格式:
            {"symbol": "600519", "price": 1440.0, "change_pct": -1.02, "volume_ratio": 0.96}

    Returns:
        被触发的规则列表
    """
    rules = _load_rules()
    triggered = []

    for rule in rules:
        if not rule.get("enabled"):
            continue
        if rule["symbol"] != stock_data.get("symbol"):
            continue

        cond = rule["condition"]
        thresh = rule["threshold"]
        fired = False

        if cond == "price_above" and stock_data.get("price", 0) > thresh:
            fired = True
        elif cond == "price_below" and stock_data.get("price", 0) < thresh:
            fired = True
        elif cond == "change_pct_above" and stock_data.get("change_pct", 0) > thresh:
            fired = True
        elif cond == "change_pct_below" and stock_data.get("change_pct", 0) < thresh:
            fired = True
        elif cond == "volume_ratio_above" and stock_data.get("volume_ratio", 0) > thresh:
            fired = True

        if fired:
            triggered.append({
                **rule,
                "current_value": stock_data,
            })

    return triggered
