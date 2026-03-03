"""
A 股监控分析 Agent — 入口文件
在终端运行: python main.py
"""

from langchain_core.messages import HumanMessage
from src.agent.graph import build_graph


def main():
    print("=" * 50)
    print("  A 股智能分析助手")
    print("  输入你的问题，输入 q 退出")
    print("=" * 50)

    agent = build_graph()

    # 维护对话历史，实现多轮对话
    messages = []

    while True:
        user_input = input("\n你: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ("q", "quit", "exit"):
            print("再见！")
            break

        messages.append(HumanMessage(content=user_input))

        print("助手: ", end="", flush=True)

        result = agent.invoke({"messages": messages})

        ai_message = result["messages"][-1]
        print(ai_message.content)

        # 把完整的消息历史更新回来（包含系统提示和 AI 回复）
        messages = result["messages"]


if __name__ == "__main__":
    main()
