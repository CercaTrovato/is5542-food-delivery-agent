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

ORDER_SCAN_RE = re.compile(r"ORD[\s\-_]*[0-9OIL]{1,12}(?![0-9A-Z])", re.IGNORECASE)
PURE_LOOKUP_RE = re.compile(r"送到哪|几点送到|到哪了|查一下进度|查看进度|多少钱|实付|什么菜|订单详情")
PRAISE_NO_CLAIM_RE = re.compile(
    r"(?:不是|不用|不要|无需|不需要|不必)(?:要|申请)?(?:申请|赔付?|赔偿|补偿|发券)|辛苦了|表扬|点赞|态度很好"
)


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


def _normalize_id(raw_match: str) -> str:
    raw_id = re.sub(r"[\s\-_]+", "", raw_match.upper())
    suffix = raw_id[3:].translate(str.maketrans({"O": "0", "I": "1", "L": "1"}))
    if suffix.isdigit():
        if len(suffix) < 3:
            suffix = suffix.zfill(3)
        elif len(suffix) > 3 and suffix.startswith("0"):
            stripped = suffix.lstrip("0") or "0"
            if len(stripped) <= 3:
                suffix = stripped.zfill(3)
    return "ORD" + suffix


class ScriptedOrderModel(BaseChatModel):
    """Deterministic teaching stand-in that emits standard single or multi-order tool-call messages."""

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
            text = last.text or ""
            matches = ORDER_SCAN_RE.findall(text)
            if matches:
                seen_ids: list[str] = []
                for m in matches:
                    nid = _normalize_id(m)
                    if nid not in seen_ids:
                        seen_ids.append(nid)
                is_lookup = bool(PURE_LOOKUP_RE.search(text) or PRAISE_NO_CLAIM_RE.search(text))
                purpose = "lookup" if (is_lookup and not re.search(r"能赔|可以赔|申请补偿|申请赔付", text)) else "compensation"
                response = AIMessage(
                    content="",
                    tool_calls=[
                        {"name": "query_order", "args": {"order_id": nid, "purpose": purpose}, "id": uuid4().hex}
                        for nid in seen_ids[:4]
                    ],
                )
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
