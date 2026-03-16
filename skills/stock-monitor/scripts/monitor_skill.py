"""
监控管理 Skill。

让用户通过自然语言对话来管理股票监控规则，例如：
- "帮我监控茅台，跌破1400就提醒我"
- "查看我的监控列表"
- "删除第2条规则"
"""

from langchain_core.tools import tool
from src.monitor.rules import add_rule, list_rules, remove_rule


@tool
def add_stock_monitor(
    symbol: str,
    condition: str,
    threshold: float,
    description: str = "",
) -> str:
    """添加一条股票监控规则。当条件触发时系统会发出告警。

    Args:
        symbol: 股票代码，6位数字
        condition: 条件类型，可选值：
            "price_above" - 价格高于某值时告警
            "price_below" - 价格低于某值时告警
            "change_pct_above" - 涨幅超过某百分比时告警
            "change_pct_below" - 跌幅超过某百分比时告警（用负数，如 -5 表示跌超5%）
        threshold: 阈值数字
        description: 规则的文字描述
    """
    try:
        rule = add_rule(symbol, condition, threshold, description)
        return (
            f"监控规则已添加！\n"
            f"  规则ID: {rule['id']}\n"
            f"  股票: {symbol}\n"
            f"  条件: {condition}\n"
            f"  阈值: {threshold}\n"
            f"  描述: {rule['description']}\n\n"
            f"启动监控服务: python -m src.monitor.scheduler"
        )
    except Exception as e:
        return f"添加规则失败: {e}"


@tool
def list_stock_monitors() -> str:
    """查看当前设置的所有股票监控规则。"""
    try:
        rules = list_rules()
        if not rules:
            return "暂无监控规则。你可以说\"帮我监控茅台，跌破1400就提醒我\"来添加。"

        lines = [f"当前共 {len(rules)} 条监控规则：\n"]
        for r in rules:
            status = "启用" if r.get("enabled") else "禁用"
            last = r.get("last_triggered") or "未触发过"
            lines.append(
                f"  [{r['id']}] {r['description']}\n"
                f"      股票:{r['symbol']} | 条件:{r['condition']} | 阈值:{r['threshold']} | {status}\n"
                f"      创建:{r['created_at'][:16]} | 上次触发:{last}"
            )
            lines.append("")

        lines.append("启动监控: python -m src.monitor.scheduler")
        return "\n".join(lines)
    except Exception as e:
        return f"查询规则失败: {e}"


@tool
def remove_stock_monitor(rule_id: int) -> str:
    """删除一条股票监控规则。

    Args:
        rule_id: 规则编号（通过查看监控列表获取）
    """
    try:
        if remove_rule(rule_id):
            return f"规则 {rule_id} 已删除。"
        else:
            return f"未找到规则 {rule_id}，请先查看监控列表确认编号。"
    except Exception as e:
        return f"删除规则失败: {e}"


MONITOR_TOOLS = [add_stock_monitor, list_stock_monitors, remove_stock_monitor]
