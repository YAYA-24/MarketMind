"""
定时监控 + 告警推送。

功能：
1. 定时拉取已监控股票的实时行情
2. 匹配规则 → 触发告警
3. 推送通知（终端输出 + 写入日志，可扩展为邮件/微信等）
4. 盘前自动生成"今日看点"摘要

用法:
  启动监控: python -m src.monitor.scheduler
  盘前摘要: python -m src.monitor.scheduler --morning
"""

import re
import os
import sys
import time
import json
import requests
from datetime import datetime

from src.monitor.rules import list_rules, check_rules

SINA_HEADERS = {"Referer": "https://finance.sina.com.cn"}
ALERT_LOG = "./data/alerts.log"


def _get_sina_prefix(symbol: str) -> str:
    return f"sh{symbol}" if symbol.startswith("6") else f"sz{symbol}"


def _fetch_realtime(symbol: str) -> dict | None:
    """从新浪获取单只股票实时数据。"""
    try:
        sina_sym = _get_sina_prefix(symbol)
        r = requests.get(
            f"https://hq.sinajs.cn/list={sina_sym}",
            headers=SINA_HEADERS, timeout=10,
        )
        r.encoding = "gbk"
        match = re.search(r'"(.*)"', r.text)
        if not match or not match.group(1):
            return None
        fields = match.group(1).split(",")
        if len(fields) < 32:
            return None

        price = float(fields[3])
        prev_close = float(fields[2])
        change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0

        return {
            "symbol": symbol,
            "name": fields[0],
            "price": price,
            "change_pct": round(change_pct, 2),
            "volume": int(fields[8]),
            "amount": float(fields[9]),
            "time": f"{fields[30]} {fields[31]}",
        }
    except Exception:
        return None


def _send_alert(rule: dict, stock: dict):
    """发送告警通知。当前实现为终端输出 + 写日志，可扩展。"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = (
        f"[告警] {ts}\n"
        f"  股票: {stock.get('name', '')} ({rule['symbol']})\n"
        f"  条件: {rule['description']}\n"
        f"  当前价: {stock.get('price', 'N/A')} | 涨跌幅: {stock.get('change_pct', 'N/A')}%\n"
    )

    print(msg)

    os.makedirs(os.path.dirname(ALERT_LOG), exist_ok=True)
    with open(ALERT_LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def run_check_once():
    """执行一次全量规则检查。"""
    rules = list_rules()
    if not rules:
        print("暂无监控规则。")
        return

    symbols = list(set(r["symbol"] for r in rules if r.get("enabled")))
    if not symbols:
        print("暂无启用的监控规则。")
        return

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 检查 {len(symbols)} 只股票, {len(rules)} 条规则...")

    for symbol in symbols:
        data = _fetch_realtime(symbol)
        if not data:
            continue

        triggered = check_rules(data)
        for rule in triggered:
            _send_alert(rule, data)

        if not triggered:
            print(f"  {data['name']}({symbol}): {data['price']:.2f} ({data['change_pct']:+.2f}%) - 无触发")

        time.sleep(0.5)


def run_monitor(interval: int = 30):
    """
    启动持续监控循环。

    Args:
        interval: 检查间隔（秒），默认30秒
    """
    print("=" * 50)
    print("  A 股监控系统启动")
    print(f"  检查间隔: {interval} 秒")
    print("  按 Ctrl+C 停止")
    print("=" * 50)

    while True:
        try:
            now = datetime.now()
            hour, minute = now.hour, now.minute

            # 只在交易时间检查（9:15-15:05）
            trading = (9 <= hour < 15) or (hour == 15 and minute <= 5)
            if not trading:
                # 非交易时间每 5 分钟检查一次时间
                print(f"[{now.strftime('%H:%M:%S')}] 非交易时间，等待中...")
                time.sleep(300)
                continue

            run_check_once()
            time.sleep(interval)

        except KeyboardInterrupt:
            print("\n监控已停止。")
            break
        except Exception as e:
            print(f"检查出错: {e}")
            time.sleep(interval)


def generate_morning_brief():
    """
    盘前"今日看点"自动摘要。

    汇总：已监控股票的前一日收盘数据 + 联网搜索最新市场动态 → 大模型生成摘要。
    """
    try:
        from src.agent.graph import build_graph
        from langchain_core.messages import HumanMessage

        rules = list_rules()
        symbols = list(set(r["symbol"] for r in rules if r.get("enabled")))

        if not symbols:
            print("暂无监控股票，请先添加监控规则。")
            return

        stock_list = "、".join(symbols)
        prompt = (
            f"请为我生成今日盘前看点摘要。我正在监控以下股票: {stock_list}。\n"
            f"请帮我：\n"
            f"1. 查询这些股票的最新行情\n"
            f"2. 搜索今天的重要财经新闻和市场动态\n"
            f"3. 综合以上信息，生成一份简洁的'今日看点'摘要，"
            f"包括大盘研判、个股动态、需要关注的风险和机会"
        )

        print("=" * 50)
        print("  正在生成盘前看点摘要...")
        print("=" * 50)

        agent = build_graph()
        result = agent.invoke({"messages": [HumanMessage(content=prompt)]})
        brief = result["messages"][-1].content

        print(brief)

        # 保存到文件
        date_str = datetime.now().strftime("%Y%m%d")
        brief_dir = "./data/briefs"
        os.makedirs(brief_dir, exist_ok=True)
        filepath = os.path.join(brief_dir, f"morning_brief_{date_str}.md")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# 盘前看点 {datetime.now().strftime('%Y-%m-%d')}\n\n")
            f.write(brief)
        print(f"\n摘要已保存到: {filepath}")

    except Exception as e:
        print(f"生成摘要失败: {e}")


if __name__ == "__main__":
    if "--morning" in sys.argv:
        generate_morning_brief()
    else:
        run_monitor()
