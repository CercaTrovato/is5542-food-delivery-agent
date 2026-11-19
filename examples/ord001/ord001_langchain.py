# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = [
#     "langgraph==1.2.19",
#     "langchain==1.4.9",
#     "langchain-openai==1.7.4",
# ]
# ///

"""Use LangChain to expose the ORD001 fixture as a read-only tool."""

import argparse
import json
import os
import re
from uuid import uuid4

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from ord001_graph import lookup_order


@tool
def query_order(order_id: str) -> dict:
    """查询当前模拟顾客的订单，并返回订单状态、预计和实际送达时间。"""
    order = lookup_order(order_id)
    if order is None:
        return {"found": False, "message": "查不到这笔模拟订单。"}
    return {"found": True, **order}


def build_agent(model):
    return create_agent(
        model=model,
        tools=[query_order],
        system_prompt=(
            "你是模拟外卖客服。没有订单号时先追问。"
            "有订单号时先调用 query_order，按工具返回的订单事实回复。"
            "查不到就说明无法核实。你的权限只有查单，不能批准或承诺发券。"
        ),
    )


class ScriptedOrderModel(BaseChatModel):
    """Deterministic teaching stand-in that emits standard tool-call messages."""

    @property
    def _llm_type(self) -> str:
        return "ord001-scripted-model"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        last = messages[-1]
        if isinstance(last, ToolMessage):
            order = json.loads(last.text)
            if order["found"]:
                response = AIMessage(content=(
                    f'{order["order_id"]} 已送达，'
                    f'预计 {order["expected_at"]}，实际 {order["delivered_at"]}。'
                ))
            else:
                response = AIMessage(content="未找到这笔订单，请核对订单号。")
        else:
            match = re.search(r"ORD[\s\-_]*[0-9OIL]{1,12}(?![0-9A-Z])", last.text, re.IGNORECASE)
            if match:
                raw_id = re.sub(r"[\s\-_]+", "", match.group().upper())
                norm_id = "ORD" + raw_id[3:].translate(str.maketrans({"O": "0", "I": "1", "L": "1"}))
                response = AIMessage(content="", tool_calls=[{
                    "name": "query_order",
                    "args": {"order_id": norm_id},
                    "id": uuid4().hex,
                }])
            else:
                response = AIMessage(content="请提供订单号，或从「我的订单」中选择。")

        return ChatResult(generations=[ChatGeneration(message=response)])


def build_studio_lookup():
    model_id = os.getenv("ORD001_CHAT_MODEL")
    model = init_chat_model(model_id) if model_id else ScriptedOrderModel()
    return build_agent(model)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", help="显式启用模型调用，例如 openai:你的模型ID")
    parser.add_argument("--message", default="请查 ORD001，告诉我这笔外卖几点送到。")
    args = parser.parse_args()

    if not args.model:
        order = query_order.invoke({"order_id": "ORD001"})
        print(json.dumps(order, ensure_ascii=False))
        return

    agent = build_agent(init_chat_model(args.model))
    result = agent.invoke({"messages": [{"role": "user", "content": args.message}]})
    print(result["messages"][-1].text)


if __name__ == "__main__":
    main()
