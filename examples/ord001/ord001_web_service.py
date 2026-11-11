"""Service layer for the ORD001 web demo: runs both graphs, keeps one review thread per ticket, logs each turn."""

import json
import logging
import os
import threading
import time
from collections import defaultdict, deque
from dataclasses import asdict
from pathlib import Path
from urllib.parse import urlsplit

from openai import APIConnectionError, APIStatusError
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from ord001_langchain import ScriptedOrderModel
from ord001_policy import load_policy
from ord001_web_graphs import CustomerContext, build_customer_graph, build_review_graph
from ord001_web_store import DECISION_STATUS, DemoData, TicketStore, now_text

log = logging.getLogger("ord001_web")
CONFIRM_ANSWERS = ("confirm", "cancel")


class ServiceError(Exception):
    """An expected refusal that the web layer turns into an HTTP status."""

    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def default_model(config_path=None):
    config_path = config_path or os.getenv("ORD001_MODEL_CONFIG")
    if config_path:
        config = json.loads(Path(config_path).expanduser().read_text(encoding="utf-8"))
        if not isinstance(config, dict) or any(
            not isinstance(config.get(key), str) or not config[key].strip()
            for key in ("model", "base_url", "api_key")
        ):
            raise ValueError("模型配置须包含 model、base_url、api_key 三个非空文本字段。")
        base = urlsplit(config["base_url"])
        if base.scheme != "https" or not base.hostname or base.username or base.password or base.query or base.fragment:
            raise ValueError("模型 base_url 必须是 HTTPS 服务地址，不能包含凭据、查询参数或片段。")
        options = {
            "model_provider": "openai", "model": config["model"].strip(),
            "base_url": config["base_url"].rstrip("/"), "api_key": config["api_key"].strip(),
            "temperature": 0.4, "max_tokens": 800, "timeout": 30, "max_retries": 0,
        }
        if base.hostname == "api.deepseek.com":
            options["extra_body"] = {"thinking": {"type": "disabled"}}
        return init_chat_model(**options), f"openai:{options['model']}"
    model_id = os.getenv("ORD001_CHAT_MODEL")
    if model_id:
        return init_chat_model(model_id, timeout=30, max_retries=0), model_id
    return ScriptedOrderModel(), "ord001-scripted-model"


def visible_messages(messages) -> list[dict]:
    """Customer and assistant text plus one line per order lookup. Tool payloads stay on the server."""
    items = []
    for message in messages:
        if isinstance(message, HumanMessage):
            items.append({"role": "customer", "text": message.text})
        elif isinstance(message, AIMessage):
            for call in message.tool_calls:
                items.append({"role": "tool", "text": f"查单工具 query_order：{call['args'].get('order_id', '')}"})
            if message.text:
                items.append({"role": "assistant", "text": message.text})
    return items


def first_request(interrupts, kind: str) -> dict | None:
    for item in interrupts or ():
        if isinstance(item.value, dict) and item.value.get("kind") == kind:
            return item.value
    return None


def requested_order(messages) -> str | None:
    for message in reversed(messages):
        for call in getattr(message, "tool_calls", None) or ():
            return call["args"].get("order_id")
    return None


def token_usage(messages) -> dict | None:
    total = {}
    for message in messages:
        for key, value in (getattr(message, "usage_metadata", None) or {}).items():
            if isinstance(value, int):
                total[key] = total.get(key, 0) + value
    return total or None


def customer_copy(ticket: dict) -> dict:
    # The customer sees the decision and the note, not which reviewer made it.
    return {key: value for key, value in ticket.items() if key != "reviewer_id"}


class DemoService:
    """Customer turns, confirmations and reviews. Identity always comes from the caller's server session."""

    def __init__(self, *, model=None, model_label=None, model_config_path=None,
                 data=None, policy=None, db_path=":memory:"):
        if model is None:
            model, model_label = default_model(model_config_path)
        self.model = model
        self.model_label = model_label or getattr(model, "_llm_type", type(model).__name__)
        self.data = data or DemoData()
        self.policy = policy or load_policy()
        self.store = TicketStore(db_path)
        self.run_log = deque(maxlen=1000)
        self._guard = threading.Lock()
        self._thread_locks = defaultdict(threading.Lock)
        self._review_lock = threading.RLock()
        self._build_graphs()

    def _build_graphs(self) -> None:
        self.customer_graph = build_customer_graph(self.model, self.data, self.store, self.policy, InMemorySaver())
        self.review_graph = build_review_graph(self.store, InMemorySaver())

    def info(self) -> dict:
        return {
            "policy": asdict(self.policy),
            "data_version": self.data.version,
            "service_date": self.data.service_date,
            "model": self.model_label,
            "model_mode": "scripted" if isinstance(self.model, ScriptedOrderModel) else "live",
            "customers": list(self.data.customers.values()),
            "reviewers": list(self.data.reviewers.values()),
        }

    def _record(self, **entry) -> None:
        entry = {"at": now_text(), **entry, "policy_version": self.policy.version, "model": self.model_label}
        self.run_log.append(entry)
        log.info(json.dumps(entry, ensure_ascii=False))

    @staticmethod
    def _thread(thread_id: str) -> dict:
        return {"configurable": {"thread_id": thread_id}}

    def _lock(self, thread_id: str) -> threading.Lock:
        with self._guard:
            return self._thread_locks[thread_id]

    # Customer side

    def customer_view(self, thread_id: str, customer_id: str) -> dict:
        snapshot = self.customer_graph.get_state(self._thread(thread_id))
        return {
            "messages": visible_messages((snapshot.values or {}).get("messages", [])),
            "confirmation": first_request(snapshot.interrupts, "confirm_submission"),
            "tickets": self.customer_tickets(customer_id),
        }

    def send_message(self, thread_id: str, customer_id: str, text: str) -> dict:
        with self._lock(thread_id):
            snapshot = self.customer_graph.get_state(self._thread(thread_id))
            if first_request(snapshot.interrupts, "confirm_submission"):
                raise ServiceError(409, "confirmation_pending", "请先确认或取消当前的提交。")
            payload = {"messages": [HumanMessage(content=text)]}
            return self._run(thread_id, customer_id, payload, "customer_message", snapshot)

    def confirm(self, thread_id: str, customer_id: str, answer: str) -> dict:
        if answer not in CONFIRM_ANSWERS:
            raise ServiceError(400, "invalid_answer", "answer 只能是 confirm 或 cancel。")
        with self._lock(thread_id):
            snapshot = self.customer_graph.get_state(self._thread(thread_id))
            if not first_request(snapshot.interrupts, "confirm_submission"):
                raise ServiceError(409, "nothing_to_confirm", "当前没有待确认的提交。")
            return self._run(thread_id, customer_id, Command(resume=answer), f"customer_{answer}", snapshot)

    def _run(self, thread_id: str, customer_id: str, payload, event: str, snapshot) -> dict:
        config = self._thread(thread_id)
        before = len((snapshot.values or {}).get("messages", []))
        waiting = first_request(snapshot.interrupts, "confirm_submission")
        started = time.perf_counter()
        try:
            result = self.customer_graph.invoke(payload, config, context=CustomerContext(customer_id))
        except APIStatusError as exc:
            self._record(event="model_error", outcome="provider_error", http_status=exc.status_code)
            if exc.status_code in (401, 403):
                message = "客服暂时无法连接，请稍后重试。管理员需检查模型服务配置。"
            elif exc.status_code == 402:
                message = "客服暂时无法连接，请稍后重试。管理员需检查模型账户余额。"
            elif exc.status_code == 429:
                message = "客服当前繁忙，请稍后再试。你的输入已保留。"
            else:
                message = "客服服务暂时不可用，请稍后重试。你的输入已保留。"
            raise ServiceError(503, "model_unavailable", message) from None
        except APIConnectionError:
            self._record(event="model_error", outcome="connection_error")
            raise ServiceError(503, "model_unavailable", "客服连接超时或中断，请重试。你的输入已保留。") from None
        latency_ms = round((time.perf_counter() - started) * 1000)
        new_messages = result.get("messages", [])[before:]
        ticket = self.store.get(result["ticket_id"]) if result.get("ticket_id") else None
        if result.get("outcome") == "ticket_created":
            self._open_review(ticket["ticket_id"])
        confirmation = first_request(result.get("__interrupt__"), "confirm_submission")
        order_id = requested_order(new_messages) or (confirmation or waiting or ticket or {}).get("order_id")
        self._record(event=event, customer_id=customer_id, thread_id=thread_id, outcome=result.get("outcome"),
                     reason_code=result.get("reason_code"), order_id=order_id,
                     ticket_id=ticket["ticket_id"] if ticket else None,
                     latency_ms=latency_ms, usage=token_usage(new_messages))
        return {
            "outcome": result.get("outcome"),
            "reason_code": result.get("reason_code"),
            "messages": visible_messages(new_messages),
            "confirmation": confirmation,
            "ticket": customer_copy(ticket) if ticket else None,
        }

    def customer_orders(self, customer_id: str) -> list[dict]:
        return self.data.orders_for_customer(customer_id)

    def customer_tickets(self, customer_id: str) -> list[dict]:
        return [customer_copy(ticket) for ticket in self.store.tickets(customer_id=customer_id)]

    def customer_ticket(self, customer_id: str, ticket_id: str) -> dict:
        ticket = self.store.get(ticket_id)
        if ticket is None or ticket["customer_id"] != customer_id:
            raise ServiceError(404, "ticket_not_found", "当前账号下没有这张工单。")
        timeline = [{"at": event["at"], "action": event["action"], "note": event["note"]}
                    for event in self.store.events(ticket_id)]
        return {"ticket": customer_copy(ticket), "timeline": timeline}

    def submit_information(self, customer_id: str, ticket_id: str, text: str) -> dict:
        if not isinstance(text, str) or not text.strip():
            raise ServiceError(400, "invalid_text", "请填写补充信息。")
        text = text.strip()
        if len(text) > 500:
            raise ServiceError(400, "text_too_long", "补充信息不能超过 500 个字。")
        with self._review_lock:
            ticket = self.store.get(ticket_id)
            if ticket is None or ticket["customer_id"] != customer_id:
                raise ServiceError(404, "ticket_not_found", "当前账号下没有这张工单。")
            if ticket["status"] != "needs_info":
                raise ServiceError(409, "information_not_requested", "这份申请当前无需补充信息。")
            ticket = self.store.submit_information(ticket_id, customer_id=customer_id, text=text)
            if ticket is None:
                raise ServiceError(409, "information_not_requested", "这份申请当前无需补充信息。")
            self._open_review(ticket_id)
            self._record(event="customer_information", customer_id=customer_id,
                         outcome="pending", order_id=ticket["order_id"], ticket_id=ticket_id)
            return self.customer_ticket(customer_id, ticket_id)

    # Review side

    @staticmethod
    def _review_thread(ticket_id: str) -> dict:
        return {"configurable": {"thread_id": f"review-{ticket_id}"}}

    def _ticket_or_404(self, ticket_id: str) -> dict:
        ticket = self.store.get(ticket_id)
        if ticket is None:
            raise ServiceError(404, "ticket_not_found", "没有这张工单。")
        return ticket

    def _open_review(self, ticket_id: str) -> dict | None:
        """Start the review graph for a pending ticket once and return its approval request."""
        with self._review_lock:
            if self._ticket_or_404(ticket_id)["status"] != "pending":
                return None
            config = self._review_thread(ticket_id)
            snapshot = self.review_graph.get_state(config)
            if snapshot.next:
                return first_request(snapshot.interrupts, "review_ticket")
            result = self.review_graph.invoke({"ticket_id": ticket_id}, config)
            return first_request(result.get("__interrupt__"), "review_ticket")

    def review_tickets(self) -> dict:
        with self._review_lock:
            tickets = self.store.tickets()
            return {
                "pending": [{**ticket, "review_request": self._open_review(ticket["ticket_id"])
                             if ticket["status"] == "pending" else None}
                            for ticket in tickets if ticket["status"] in ("pending", "needs_info")],
                "decided": [ticket for ticket in tickets if ticket["status"] in ("approved", "rejected")],
            }

    def runs(self, limit: int = 100) -> list[dict]:
        return list(self.run_log)[-limit:]

    def review_detail(self, ticket_id: str) -> dict:
        ticket = self._ticket_or_404(ticket_id)
        request = self._open_review(ticket_id) if ticket["status"] == "pending" else None
        return {"ticket": ticket, "events": self.store.events(ticket_id), "request": request}

    def decide(self, ticket_id: str, reviewer_id: str, decision: str, note: str | None) -> dict:
        if not isinstance(decision, str) or decision not in DECISION_STATUS:
            raise ServiceError(400, "invalid_decision", "不支持这个处理操作。")
        if decision == "request_info":
            if not isinstance(note, str) or not note.strip():
                raise ServiceError(400, "information_question_required", "请填写需要顾客补充的内容。")
            note = note.strip()
            if len(note) > 200:
                raise ServiceError(400, "note_too_long", "问题不能超过 200 个字。")
        if reviewer_id not in self.data.reviewers:
            raise ServiceError(403, "not_a_reviewer", "当前身份没有审批权限。")
        with self._review_lock:
            current = self._ticket_or_404(ticket_id)
            if current["status"] == "needs_info":
                raise ServiceError(409, "customer_information_pending", "正在等待顾客补充信息。")
            if current["status"] != "pending":
                raise ServiceError(409, "ticket_already_decided", "这张工单已经处理过。")
            self._open_review(ticket_id)
            started = time.perf_counter()
            answer = {"decision": decision, "reviewer_id": reviewer_id, "note": note}
            result = self.review_graph.invoke(Command(resume=answer), self._review_thread(ticket_id))
            latency_ms = round((time.perf_counter() - started) * 1000)
            ticket = result.get("ticket")
            if ticket is None or ticket["status"] == "pending":
                raise ServiceError(409, "ticket_already_decided", "这张工单已经处理过。")
        self._record(event="review_decision", reviewer_id=reviewer_id, customer_id=ticket["customer_id"],
                     outcome=ticket["status"], order_id=ticket["order_id"], ticket_id=ticket_id,
                     latency_ms=latency_ms)
        return {"ticket": ticket, "events": self.store.events(ticket_id)}

    def reset(self) -> None:
        """Clear tickets and conversations. Mock accounts, orders and the rule stay as loaded."""
        with self._review_lock, self._guard:
            self.store.reset()
            self._thread_locks.clear()
            self.run_log.clear()
            self._build_graphs()
        self._record(event="reset")
