"""Studio graph for an ORD001 delay claim with human approval."""

import json
import os

from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from ord001_graph import evaluate_order, review
from ord001_langchain import ScriptedOrderModel, query_order


class CompensationState(MessagesState, total=False):
    order_id: str | None
    expected_at: str | None
    delivered_at: str | None
    late_minutes: int | None
    status: str
    message: str


SYSTEM_PROMPT = SystemMessage(content=(
    "你在处理模拟外卖配送延误补偿。用户咨询或申请补偿时，"
    "如果当前对话没有明确订单号，请先追问；如果已给出订单号，调用一次 query_order。"
    "不要猜测订单号、送达时间或审批结果。工具返回后，程序会判断资格和处理审批。"
    "如果用户的诉求和延误补偿无关，请说明本流程的用途。"
))


def calculate_delay(state: CompensationState) -> dict:
    """Apply the shared exercise policy to facts returned by the tool."""
    tool_result = state["messages"][-1]
    if tool_result.status == "error":
        message = "订单查询失败，暂时无法判断补偿资格。"
        return {"status": "query_failed", "message": message, "messages": [AIMessage(content=message)]}

    result = json.loads(tool_result.text)
    order = result if result["found"] else None
    outcome = evaluate_order(order)
    if order is not None:
        outcome.update(
            order_id=order["order_id"],
            expected_at=order["expected_at"],
            delivered_at=order["delivered_at"],
        )
    if outcome["status"] == "pending":
        outcome["message"] = f"订单晚到 {outcome['late_minutes']} 分钟，补偿草稿待人工审批。"
    return {**outcome, "messages": [AIMessage(content=outcome["message"])]}


def review_claim(state: CompensationState) -> dict:
    result = review(state)
    return {**result, "messages": [AIMessage(content=result["message"])]}


def build_compensation_graph(model, checkpointer=None):
    model_with_tools = model.bind_tools([query_order], parallel_tool_calls=False)

    async def call_model(state: CompensationState) -> dict:
        reply = await model_with_tools.ainvoke([SYSTEM_PROMPT, *state["messages"]])
        return {
            "messages": [reply],
            "order_id": None,
            "expected_at": None,
            "delivered_at": None,
            "late_minutes": None,
            "status": "checking_order" if reply.tool_calls else "no_tool_call",
            "message": reply.text,
        }

    graph = StateGraph(CompensationState, input_schema=MessagesState)
    graph.add_node("model", call_model)
    graph.add_node("tools", ToolNode([query_order]))
    graph.add_node("calculate_delay", calculate_delay)
    graph.add_node("review", review_claim)
    graph.add_edge(START, "model")
    graph.add_conditional_edges(
        "model",
        lambda state: "lookup" if state["messages"][-1].tool_calls else "reply",
        {"lookup": "tools", "reply": END},
    )
    graph.add_edge("tools", "calculate_delay")
    graph.add_conditional_edges(
        "calculate_delay",
        lambda state: "pending" if state["status"] == "pending" else "finished",
        {"pending": "review", "finished": END},
    )
    graph.add_edge("review", END)
    return graph.compile(checkpointer=checkpointer)


def build_studio_compensation():
    model_id = os.getenv("ORD001_CHAT_MODEL")
    model = init_chat_model(model_id) if model_id else ScriptedOrderModel()
    return build_compensation_graph(model)
