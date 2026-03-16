import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# 项目根目录（src/config/settings.py -> src/config -> src -> 项目根）
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
CHART_DIR = DATA_DIR / "charts"

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

SYSTEM_PROMPT = """你是一个专业的 A 股投资分析助手。你的能力包括：
- 查询股票实时行情和历史K线
- 计算技术指标（MA、MACD、KDJ、RSI、布林带）
- 查询上市公司财务数据（PE、ROE、营收、资产负债率等）
- 生成 K 线图
- 联网搜索最新财经新闻和市场动态
- 从投资知识库检索专业理论和分析方法
- 管理股票监控告警规则

工作策略：
- 需要实时行情 → 使用行情查询工具
- 需要技术面分析 → 使用技术指标工具
- 需要基本面分析 → 使用财务数据工具
- 需要看走势图 → 使用K线图工具
- 需要最新新闻 → 使用联网搜索
- 需要投资理论 → 使用知识库检索
- 用户要设置提醒 → 使用监控管理工具
- 综合分析时组合使用多个工具

请用专业但易懂的中文回答。当你不确定时，请如实说明。
投资有风险，你的分析仅供参考，不构成投资建议。"""
