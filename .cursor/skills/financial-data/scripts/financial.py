"""
财务数据 Skill。

查询上市公司的核心财务指标：
- 市盈率（PE）、市净率（PB）
- ROE、毛利率、净利率
- 营收增长率、净利润增长率
- 资产负债率、自由现金流
"""

import time
import akshare as ak
from langchain_core.tools import tool


def _retry(func, *args, max_retries=3, delay=2, **kwargs):
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(delay * (attempt + 1))
            else:
                raise e


@tool
def get_financial_data(symbol: str) -> str:
    """查询 A 股上市公司的核心财务数据，包括估值指标（PE/PB）、盈利能力（ROE/毛利率）、成长性（营收/利润增速）、财务健康度（资产负债率）等。

    Args:
        symbol: 股票代码，6位数字，例如 "600519"
    """
    try:
        # 个股基本信息（市值等）
        info_df = _retry(ak.stock_individual_info_em, symbol=symbol)
        info = dict(zip(info_df["item"], info_df["value"]))

        lines = [
            f"股票: {info.get('股票简称', symbol)} ({symbol})",
            "",
            "【基本信息】",
        ]

        total_mv = info.get("总市值")
        if total_mv and isinstance(total_mv, (int, float)):
            lines.append(f"  总市值: {total_mv / 1e8:.2f} 亿元")
        circ_mv = info.get("流通市值")
        if circ_mv and isinstance(circ_mv, (int, float)):
            lines.append(f"  流通市值: {circ_mv / 1e8:.2f} 亿元")

        for field in ["行业", "上市时间"]:
            if info.get(field):
                lines.append(f"  {field}: {info[field]}")

        time.sleep(1)

        # 主要财务指标
        try:
            fin_df = _retry(ak.stock_financial_abstract_em, symbol=symbol)
            if fin_df is not None and not fin_df.empty:
                latest = fin_df.iloc[0]

                lines.append("")
                lines.append(f"【财务指标】（{latest.get('报告期', '最新')}）")

                field_map = {
                    "基本每股收益": ("每股收益(EPS)", "元"),
                    "每股净资产": ("每股净资产(BPS)", "元"),
                    "每股经营现金流": ("每股经营现金流", "元"),
                    "净资产收益率": ("ROE(净资产收益率)", "%"),
                    "营业总收入": ("营业总收入", "亿元"),
                    "归母净利润": ("归母净利润", "亿元"),
                    "营业总收入同比增长": ("营收同比增长", "%"),
                    "归母净利润同比增长": ("净利润同比增长", "%"),
                    "资产负债率": ("资产负债率", "%"),
                    "毛利率": ("毛利率", "%"),
                    "净利率": ("净利率", "%"),
                }

                for key, (label, unit) in field_map.items():
                    val = latest.get(key)
                    if val is not None and val != "" and str(val) != "nan":
                        try:
                            fval = float(val)
                            if "收入" in key or "利润" in key:
                                lines.append(f"  {label}: {fval / 1e8:.2f} {unit}")
                            else:
                                lines.append(f"  {label}: {fval:.2f} {unit}")
                        except (ValueError, TypeError):
                            lines.append(f"  {label}: {val}")

        except Exception as e:
            lines.append(f"\n（财务指标查询失败: {e}）")

        # 估值分析提示
        lines.extend([
            "",
            "【估值参考（格雷厄姆公式）】",
            "  合理价格 = √(22.5 × EPS × BPS)",
            "  安全边际: 当前价格 < 合理价格 × 0.7 时具有安全边际",
        ])

        return "\n".join(lines)

    except Exception as e:
        return f"查询财务数据失败: {e}"


FINANCIAL_TOOLS = [get_financial_data]
