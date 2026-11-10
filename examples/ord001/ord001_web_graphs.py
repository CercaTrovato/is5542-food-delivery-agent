"""LangGraph flows behind the ORD001 web demo: the customer claim and the human review."""

import json
from dataclasses import dataclass
from typing import TypedDict

from langchain.tools import ToolRuntime, tool
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.runtime import Runtime
from langgraph.types import interrupt

from ord001_policy import evaluate_order
from ord001_web_store import DECISION_STATUS, normalize_order_id, order_facts
from ord001_web_texts import CANCELLED, NOT_VERIFIED, QUERY_FAILED, confirm_text, outcome_text, ticket_text

SYSTEM_PROMPT = SystemMessage(content=(
    "你是模拟外卖客服，处理已送达订单的配送延误补偿。"
    "对话里没有明确订单号时先追问；顾客给出订单号后调用一次 query_order。"
    "你只能查当前登录顾客的订单。资格判断、提交和审批由程序与人工完成，不要自己承诺补偿或发券。"
    "不要猜测订单号或送达时间。诉求与延误补偿无关时，说明本流程的用途。"
))
TOOL_NOT_VERIFIED = json.dumps({"found": False, "message": "当前账号下没有这笔订单，无法核实。"}, ensure_ascii=False)


@dataclass(frozen=True)
class CustomerContext:
    customer_id: str | None


class CustomerState(MessagesState, total=False):
    outcome: str
    reason_code: str | None
    claim: dict | None
    ticket_id: str | None


class ReviewState(TypedDict, total=False):
    ticket_id: str
    ticket: dict | None
    decision: str
    reviewer_id: str
    note: str | None


def current_customer(runtime) -> str | None:
    return runtime.context.customer_id if runtime.context else None


def make_order_tool(data):
    @tool(response_format="content_and_artifact")
    def query_order(order_id: str, runtime: ToolRuntime[CustomerContext]) -> tuple[str, dict]:
        """查询当前登录顾客的订单，返回送达状态、预计和实际送达时间。"""
        found, order = data.lookup_for_customer(order_id, current_customer(runtime))
        if order is None:
            # A missing order and another customer's order look the same to the model and the customer.
            return TOOL_NOT_VERIFIED, {"outcome": found, "order_id": normalize_order_id(order_id)}
        facts = {"found": True, "order_id": order["order_id"], **order_facts(order)}
        return json.dumps(facts, ensure_ascii=False), {"outcome": "found", "order": order}

    return query_order


def reply(outcome: str, reason_code: str | None, text: str, **extra) -> dict:
    return {"outcome": outcome, "reason_code": reason_code, "messages": [AIMessage(content=text)], **extra}


def build_customer_graph(model, data, store, policy, checkpointer=None):
    query_order = make_order_tool(data)
    model_with_tools = model.bind_tools([query_order], parallel_tool_calls=False)

    def agent(state: CustomerState) -> dict:
        response = model_with_tools.invoke([SYSTEM_PROMPT, *state["messages"]])
        outcome = "lookup_requested" if response.tool_calls else "not_selected"
        return {"messages": [response], "outcome": outcome, "reason_code": None, "claim": None, "ticket_id": None}

    def judge(order: dict) -> dict:
        """Reuse the ticket kept for this order and rule version, otherwise apply the rule."""
        existing = store.find(order["order_id"], policy.version)
        if existing:
            return reply("ticket_reused", None, ticket_text(existing, created=False), ticket_id=existing["ticket_id"])
        decision = evaluate_order(order_facts(order), policy)
        if decision["status"] != "pending":
            return reply(decision["status"], decision["reason_code"], outcome_text(order, decision, policy))
        claim = {
            "order_id": order["order_id"],
            "expected_at": order["expected_at"],
            "delivered_at": order["delivered_at"],
            "late_seconds": decision["late_seconds"],
            "proposed_coupon_yuan": decision["proposed_coupon_yuan"],
            "policy_version": decision["policy_version"],
        }
        return reply("awaiting_confirmation", decision["reason_code"], confirm_text(claim), claim=claim)

    def assess(state: CustomerState) -> dict:
        result = state["messages"][-1]
        artifact = result.artifact if isinstance(result, ToolMessage) else None
        if getattr(result, "status", None) == "error" or not isinstance(artifact, dict):
            return reply("query_failed", "query_failed", QUERY_FAILED)
        if artifact["outcome"] != "found":
            return reply(artifact["outcome"], "order_not_verified", NOT_VERIFIED)
        return judge(artifact["order"])

    def confirm(state: CustomerState) -> dict:
        # Nothing runs before interrupt(): LangGraph replays this node from the top on resume.
        answer = interrupt({"kind": "confirm_submission", **state["claim"]})
        if answer == "confirm":
            return {"messages": [HumanMessage(content="确认提交")], "outcome": "claim_confirmed"}
        return {"messages": [HumanMessage(content="暂不提交"), AIMessage(content=CANCELLED)],
                "outcome": "claim_cancelled", "claim": None}

    def submit(state: CustomerState, runtime: Runtime[CustomerContext]) -> dict:
        """Check ownership and the rule again on the server, then keep one pending ticket."""
        customer_id = current_customer(runtime)
        found, order = data.lookup_for_customer(state["claim"]["order_id"], customer_id)
        if order is None:
            return reply(found, "order_not_verified", NOT_VERIFIED, claim=None)
        decision = evaluate_order(order_facts(order), policy)
        if decision["status"] != "pending":
            return reply(decision["status"], decision["reason_code"], outcome_text(order, decision, policy), claim=None)
        ticket, created = store.create_or_get(customer_id=customer_id, order=order, decision=decision)
        outcome = "ticket_created" if created else "ticket_reused"
        return reply(outcome, decision["reason_code"], ticket_text(ticket, created=created),
                     claim=None, ticket_id=ticket["ticket_id"])

    graph = StateGraph(CustomerState, context_schema=CustomerContext, input_schema=MessagesState)
    graph.add_node("agent", agent)
    graph.add_node("tools", ToolNode([query_order]))
    graph.add_node("assess", assess)
    graph.add_node("confirm", confirm)
    graph.add_node("submit", submit)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", lambda s: "tools" if s["outcome"] == "lookup_requested" else END, ["tools", END])
    graph.add_edge("tools", "assess")
    graph.add_conditional_edges("assess", lambda s: "confirm" if s["outcome"] == "awaiting_confirmation" else END,
                                ["confirm", END])
    graph.add_conditional_edges("confirm", lambda s: "submit" if s["outcome"] == "claim_confirmed" else END,
                                ["submit", END])
    graph.add_edge("submit", END)
    return graph.compile(checkpointer=checkpointer)


def build_review_graph(store, checkpointer=None):
    def load_ticket(state: ReviewState) -> dict:
        return {"ticket": store.get(state["ticket_id"])}

    def review(state: ReviewState) -> dict:
        ticket = state["ticket"]
        answer = interrupt({
            "kind": "review_ticket",
            "ticket_id": ticket["ticket_id"],
            "order_id": ticket["order_id"],
            "late_seconds": ticket["late_seconds"],
            "policy_version": ticket["policy_version"],
            "proposed_coupon_yuan": ticket["proposed_coupon_yuan"],
            "information_request": ticket.get("information_request"),
            "customer_information": ticket.get("customer_information"),
            "message": "待人工审批。",
        })
        if not isinstance(answer, dict) or answer.get("decision") not in DECISION_STATUS or not answer.get("reviewer_id"):
            raise ValueError("审批输入必须包含支持的 decision，以及审批员编号")
        return {"decision": answer["decision"], "reviewer_id": answer["reviewer_id"], "note": answer.get("note")}

    def record(state: ReviewState) -> dict:
        ticket = store.decide(state["ticket_id"], decision=state["decision"],
                              reviewer_id=state["reviewer_id"], note=state.get("note"))
        return {"ticket": ticket}

    graph = StateGraph(ReviewState)
    graph.add_node("load_ticket", load_ticket)
    graph.add_node("review", review)
    graph.add_node("record", record)
    graph.add_edge(START, "load_ticket")
    graph.add_conditional_edges(
        "load_ticket",
        lambda s: "review" if s["ticket"] and s["ticket"]["status"] == "pending" else END,
        ["review", END],
    )
    graph.add_edge("review", "record")
    graph.add_edge("record", END)
    return graph.compile(checkpointer=checkpointer)
