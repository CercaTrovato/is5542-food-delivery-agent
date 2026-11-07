# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["langgraph==1.2.19"]
# ///

"""Run one simulated food-delivery claim through LangGraph."""

import argparse
import json
import os
from datetime import datetime
from typing import NotRequired, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class ApprovalState(TypedDict):
    order_id: str
    late_minutes: NotRequired[int]
    status: NotRequired[str]
    message: NotRequired[str]


def lookup_order(order_id: str) -> dict[str, str] | None:
    """Look up an order in this exercise's single-customer fixture."""
    if order_id.strip().upper() != "ORD001":
        return None
    return {
        "order_id": "ORD001",
        "status": "delivered",
        "expected_at": "18:00",
        "delivered_at": os.getenv("ORD001_DELIVERED_AT") or "18:30",
    }


def check_order(state: ApprovalState) -> dict:
    return evaluate_order(lookup_order(state["order_id"]))


def evaluate_order(order: dict[str, str] | None) -> dict:
    if order is None:
        return {"status": "not_found", "message": "查不到这笔模拟订单。"}

    expected = datetime.strptime(order["expected_at"], "%H:%M")
    delivered = datetime.strptime(order["delivered_at"], "%H:%M")
    late_minutes = int((delivered - expected).total_seconds() / 60)
    # Exercise policy only: delivered and more than 30 minutes late.
    if order["status"] == "delivered" and late_minutes > 30:
        return {"late_minutes": late_minutes, "status": "pending"}
    return {
        "late_minutes": late_minutes,
        "status": "ineligible",
        "message": "订单未达到练习中的补偿条件。",
    }


def review(state: ApprovalState) -> dict:
    decision = interrupt({
        "order_id": state["order_id"],
        "late_minutes": state["late_minutes"],
        "proposed_coupon_yuan": 10,
        "message": "待人工审批。",
    })
    if decision == "approve":
        return {"status": "approved", "message": "人工已批准 ¥10 券草稿，模拟结果已记录。"}
    if decision == "reject":
        return {"status": "rejected", "message": "人工未批准，工单已记录驳回。"}
    raise ValueError("审批输入必须是 approve 或 reject")


def build_graph(checkpointer=None):
    builder = StateGraph(ApprovalState)
    builder.add_node("check_order", check_order)
    builder.add_node("review", review)
    builder.add_edge(START, "check_order")
    builder.add_conditional_edges(
        "check_order",
        lambda state: state["status"],
        {"pending": "review", "not_found": END, "ineligible": END},
    )
    builder.add_edge("review", END)
    return builder.compile(checkpointer=checkpointer)


# The local Studio server supplies its own thread storage.
studio_graph = build_graph()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("decision", nargs="?", choices=["pending", "approve", "reject"], default="pending")
    args = parser.parse_args()

    graph = build_graph(InMemorySaver())
    config = {"configurable": {"thread_id": "ord001-practice"}}
    paused = graph.invoke({"order_id": "ORD001"}, config=config)
    if "__interrupt__" not in paused:
        print(json.dumps(paused, ensure_ascii=False))
        return

    print(json.dumps({
        "status": paused["status"],
        "approval_request": paused["__interrupt__"][0].value,
    }, ensure_ascii=False))

    if args.decision != "pending":
        finished = graph.invoke(Command(resume=args.decision), config=config)
        print(json.dumps(finished, ensure_ascii=False))


if __name__ == "__main__":
    main()
