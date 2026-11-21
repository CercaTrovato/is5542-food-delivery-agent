"""Service layer for ORD001: durable SQLite graph checkpoints, STP subrogation, P0 food-safety triage & audit chain."""

import asyncio
import json
import logging
import os
import re
import threading
import time
from collections import OrderedDict, deque
from dataclasses import asdict
from pathlib import Path
from urllib.parse import urlsplit

from openai import APIConnectionError, APIStatusError
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command

from ord001_langchain import ScriptedOrderModel
from ord001_policy import compute_actuarial_subrogation, evaluate_order, load_policy
from ord001_web_graphs import CustomerContext, SPECIAL_ISSUE_RE, build_customer_graph, build_review_graph, reply_risk
from ord001_web_store import (DECISION_STATUS, DemoData, DurableSqliteSaver, TicketStore,
                              normalize_order_id, now_text, order_facts)
from ord001_web_texts import GUARDED_REPLY

log = logging.getLogger("ord001_web")
CONFIRM_ANSWERS = ("confirm", "cancel")
ORDER_ID = re.compile(r"ORD[\s\-_]*[0-9OIL]{1,12}(?![0-9A-Z])", re.IGNORECASE)

# Disambiguated human-handoff intent: catches "受不了要投诉" / "没完没了转人工", while respecting "虽然想投诉但不用转人工".
HANDOFF_WORDS = re.compile(r"转人工|人工客服|找人工|要人工|人工服务|真人客服|活人客服|找真人|找活人|转真人|要真人|投诉")
BARE_HANDOFF = re.compile(r"\s*(?:转)?人工(?:客服|服务)?[\s!！。.~～]*")
EXPLICIT_NO_HANDOFF_RE = re.compile(
    r"(?:不用|不要|无需|不必|先不|别|不找|不转|不需要)\s*(?:帮我|给我|替我)?\s*(?:转接?|找|联系)?\s*(?:人工|真人|活人|客服|专员)"
)
LOCAL_NEGATION_RE = re.compile(
    r"(?:不是要|并非|不是|不要|不用|无需|不必|先不|不找|不转|不需要|别(?!废话|啰嗦|磨叽|扯))[^，。！？；,.!?;\n]{0,4}$"
)
QUESTION_FORMS = ("能不能", "可不可以", "可以不可以", "是不是", "要不要")
HANDOFF_LIMIT, HANDOFF_SHOWN = 500, 5
EXCERPT_LINES, EXCERPT_CHARS = 6, 160
REPLY_LIMIT = 500
MAX_LOCK_ENTRIES = 512


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
            "temperature": 0.35, "max_tokens": 800, "timeout": 30, "max_retries": 0,
        }
        if base.hostname == "api.deepseek.com":
            options["extra_body"] = {"thinking": {"type": "disabled"}}
        return init_chat_model(**options), f"openai:{options['model']}"
    ds_key = os.getenv("DEEPSEEK_API_KEY")
    if ds_key and ds_key.strip():
        model_name = (os.getenv("DEEPSEEK_MODEL") or "deepseek-chat").strip()
        base_url = (os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com/v1").rstrip("/")
        options = {
            "model_provider": "openai", "model": model_name,
            "base_url": base_url, "api_key": ds_key.strip(),
            "temperature": 0.35, "max_tokens": 800, "timeout": 30, "max_retries": 0,
            "extra_body": {"thinking": {"type": "disabled"}},
        }
        return init_chat_model(**options), f"openai:{model_name}"
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
                raw_oid = call["args"].get("order_id", "")
                items.append({"role": "tool", "text": f"查单工具 query_order：{normalize_order_id(raw_oid) if raw_oid else ''}"})
            if message.text and not message.tool_calls:
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
            raw = call["args"].get("order_id")
            return normalize_order_id(raw) if raw else None
    return None


def wants_person(text: str) -> bool:
    """True when customer asks for a human/complaint; respects '不用转人工' & catches '受不了要投诉'/'没完没了转人工'."""
    if BARE_HANDOFF.fullmatch(text):
        return True
    if EXPLICIT_NO_HANDOFF_RE.search(text):
        return False
    for match in HANDOFF_WORDS.finditer(text):
        before = text[max(0, match.start() - 8):match.start()]
        for phrase in QUESTION_FORMS:
            before = before.replace(phrase, "")
        before_tail = before.strip()
        if not LOCAL_NEGATION_RE.search(before_tail):
            return True
    return False


def focused_order(messages) -> str | None:
    """The order the chat is about now: the latest order number the customer typed or the model looked up."""
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            found = ORDER_ID.findall(message.text)
            if found:
                return normalize_order_id(found[-1])
        elif isinstance(message, AIMessage):
            for call in reversed(message.tool_calls):
                order_id = call["args"].get("order_id")
                if isinstance(order_id, str) and order_id.strip():
                    return normalize_order_id(order_id)[:32]
    return None


def handoff_copy(handoff: dict, thread_id: str | None) -> dict:
    """What the customer sees of a handoff (reviewer_id stripped for PDPO anti-doxxing protection)."""
    keys = ("handoff_id", "order_id", "status", "request_text", "reply_text", "created_at", "closed_at")
    attachments = [{**item, "url": f"/api/media/{item['attachment_id']}"} for item in handoff.get("attachments", [])]
    res = {
        **{key: handoff[key] for key in keys},
        "attachments": attachments,
        "after": handoff["after_index"] if handoff["thread_id"] == thread_id else 0,
    }
    if handoff.get("followups"):
        res["followups"] = [{"sender_role": f["sender_role"], "text": f["text"], "created_at": f["created_at"]}
                            for f in handoff["followups"]]
    return res


def review_handoff_copy(handoff: dict, order: dict | None = None) -> dict:
    result = {key: value for key, value in handoff.items() if key not in ("thread_id", "attachments")}
    result["attachments"] = [
        {
            **{key: item[key] for key in ("attachment_id", "handoff_id", "kind", "original_name", "media_type", "size_bytes", "created_at")},
            **({"forensic_note": item["forensic_note"], "duplicate_alert": item.get("duplicate_alert", False)}
               if "forensic_note" in item else {}),
        }
        for item in handoff.get("attachments", [])
    ]
    req_txt = str(handoff.get("request_text") or "")
    excerpt_txt = " ".join(x.get("text", "") for x in handoff.get("excerpt", []))
    is_food_p0 = bool(SPECIAL_ISSUE_RE.search(req_txt + " " + excerpt_txt))
    result["priority"] = "P0_FOOD_SAFETY" if is_food_p0 else ("P1_EVIDENCE" if result["attachments"] else "NORMAL")
    if order:
        result["order_summary"] = {
            k: order.get(k) for k in (
                "merchant", "amount_yuan", "status", "ordered_at", "prep_promised_at",
                "prep_done_at", "picked_up_at", "expected_at", "delivered_at",
                "liability_party", "liability_detail", "rider_protection", "gps_fence_note", "items"
            ) if k in order
        }
    return result


def token_usage(messages) -> dict | None:
    total = {}
    for message in messages:
        for key, value in (getattr(message, "usage_metadata", None) or {}).items():
            if isinstance(value, int):
                total[key] = total.get(key, 0) + value
    return total or None


CUSTOMER_INTERNAL_TICKET_KEYS = {"reviewer_id", "tenant_id", "stp_tier", "merchant_bear_yuan", "platform_bear_yuan"}
CUSTOMER_INTERNAL_ORDER_KEYS = {
    "tenant_id", "liability_party", "liability_detail", "rider_protection", "rider_sla_extended_min", "gps_fence_note"
}
CLAUSE_SPLIT_RE = re.compile(r"(?<=[，。！？；,\.!?\n])")


def customer_copy(ticket: dict) -> dict:
    """Customer sees ticket status & note; internal reviewer identity & B2B cost-split ledger stay on server."""
    return {key: value for key, value in ticket.items() if key not in CUSTOMER_INTERNAL_TICKET_KEYS}


def customer_order_copy(order: dict) -> dict:
    """Strip internal merchant/rider ledger notes before returning orders to customer API (anti-F12 snooping)."""
    return {key: value for key, value in order.items() if key not in CUSTOMER_INTERNAL_ORDER_KEYS}


class DemoService:
    """Customer turns, confirmations and reviews. Identity always comes from the caller's server session."""

    def __init__(self, *, model=None, model_label=None, model_config_path=None,
                 data=None, policy=None, db_path=":memory:", stp_auto_approve: bool = False):
        if model is None:
            model, model_label = default_model(model_config_path)
        self.model = model
        self.model_label = model_label or getattr(model, "_llm_type", type(model).__name__)
        self.data = data or DemoData()
        self.policy = policy or load_policy()
        self.store = TicketStore(db_path)
        self.stp_auto_approve = stp_auto_approve or (os.getenv("ORD001_STP_AUTO") == "1")
        self.run_log = deque(self.store.recent_audit_logs(1000, since_reset=True), maxlen=1000)
        self._guard = threading.Lock()
        self._thread_locks: OrderedDict[str, threading.Lock] = OrderedDict()
        self._async_thread_locks: OrderedDict[str, asyncio.Lock] = OrderedDict()
        self._review_lock = threading.RLock()
        self._build_graphs()

    def _build_graphs(self) -> None:
        self._customer_ckpt = DurableSqliteSaver(self.store, "customer_graph")
        self._review_ckpt = DurableSqliteSaver(self.store, "review_graph")
        self.customer_graph = build_customer_graph(
            self.model, self.data, self.store, self.policy,
            checkpointer=self._customer_ckpt,
            stp_enabled_getter=lambda: self.stp_auto_approve,
        )
        self.review_graph = build_review_graph(self.store, checkpointer=self._review_ckpt)

    def info(self) -> dict:
        return {
            "policy": asdict(self.policy),
            "stp_auto_approve": self.stp_auto_approve,
            "data_version": self.data.version,
            "service_date": self.data.service_date,
            "model": self.model_label,
            "model_mode": "scripted" if isinstance(self.model, ScriptedOrderModel) else "live",
            "customers": list(self.data.customers.values()),
            "reviewers": list(self.data.reviewers.values()),
        }

    def _reviewer_tenant(self, reviewer_id: str | None) -> str | None:
        if not reviewer_id:
            return None
        rev = self.data.reviewers.get(reviewer_id) or {}
        return rev.get("tenant_id") or "M_67REST"

    def _assert_tenant_access(self, reviewer_id: str | None, resource_tenant: str | None) -> None:
        """Object-level multi-tenant IDOR guard: block cross-tenant read/write unless reviewer has '*' scope."""
        if not reviewer_id:
            return
        rev_tenant = self._reviewer_tenant(reviewer_id)
        target = resource_tenant or "M_67REST"
        if rev_tenant != "*" and rev_tenant != target:
            raise ServiceError(403, "cross_tenant_forbidden", "无权访问或操作其他商户租户的工单数据。")

    def set_stp_mode(self, enabled: bool, reviewer_id: str) -> dict:
        self.stp_auto_approve = bool(enabled)
        auto_cleared = 0
        if self.stp_auto_approve and reviewer_id in self.data.reviewers:
            auto_cleared = self.batch_approve_green_stp(reviewer_id)["count"]
        self._record(
            event="stp_mode_changed", reviewer_id=reviewer_id,
            outcome="enabled" if self.stp_auto_approve else "disabled",
            auto_cleared_count=auto_cleared,
        )
        return {"stp_auto_approve": self.stp_auto_approve, "auto_cleared_count": auto_cleared}

    def _record(self, **entry) -> None:
        entry = {"at": now_text(), **entry, "policy_version": self.policy.version, "model": self.model_label}
        chained = self.store.append_audit_log(entry)
        self.run_log.append(chained)
        log.info(json.dumps(chained, ensure_ascii=False))

    @staticmethod
    def _thread(thread_id: str) -> dict:
        return {"configurable": {"thread_id": thread_id}}

    def _lock(self, thread_id: str) -> threading.Lock:
        with self._guard:
            if thread_id in self._thread_locks:
                self._thread_locks.move_to_end(thread_id)
                return self._thread_locks[thread_id]
            lock = threading.Lock()
            self._thread_locks[thread_id] = lock
            while len(self._thread_locks) > MAX_LOCK_ENTRIES:
                # Evict oldest unlocked entry to prevent unbounded memory growth.
                oldest_key, oldest_lock = next(iter(self._thread_locks.items()))
                if not oldest_lock.locked():
                    self._thread_locks.pop(oldest_key, None)
                else:
                    break
            return lock

    def _async_lock(self, thread_id: str) -> asyncio.Lock:
        with self._guard:
            if thread_id in self._async_thread_locks:
                self._async_thread_locks.move_to_end(thread_id)
                return self._async_thread_locks[thread_id]
            lock = asyncio.Lock()
            self._async_thread_locks[thread_id] = lock
            while len(self._async_thread_locks) > MAX_LOCK_ENTRIES:
                oldest_key, oldest_lock = next(iter(self._async_thread_locks.items()))
                if not oldest_lock.locked():
                    self._async_thread_locks.pop(oldest_key, None)
                else:
                    break
            return lock

    # Customer side

    def customer_view(self, thread_id: str, customer_id: str) -> dict:
        snapshot = self.customer_graph.get_state(self._thread(thread_id))
        messages = (snapshot.values or {}).get("messages", [])
        visible = visible_messages(messages)
        confirmation = first_request(snapshot.interrupts, "confirm_submission")
        handoffs = self.store.handoffs(customer_id=customer_id)
        own = [item for item in handoffs if item["thread_id"] == thread_id]
        handoff_order = own[-1]["order_id"] if own and own[-1]["after_index"] >= len(visible) else None
        order_id = (confirmation or {}).get("order_id") or handoff_order or focused_order(messages)
        return {
            "messages": visible,
            "confirmation": confirmation,
            "tickets": self.customer_tickets(customer_id),
            "goodwill_grants": self.store.goodwill_grants(customer_id=customer_id),
            "focus": self._focus(customer_id, order_id),
            "handoffs": [handoff_copy(item, thread_id) for item in handoffs[-HANDOFF_SHOWN:]
                         if item["thread_id"] == thread_id or item["status"] != "cancelled"],
        }

    def _focus(self, customer_id: str, order_id: str | None) -> dict | None:
        """Rule result and ticket for the order the chat is about. Another customer's order shows nothing."""
        if not order_id:
            return None
        _, order = self.data.lookup_for_customer(order_id, customer_id)
        if order is None:
            return {"order_id": order_id, "verified": False}
        decision = evaluate_order(order_facts(order), self.policy)
        ticket = self.store.find(order["order_id"], self.policy.version)
        return {
            "order_id": order["order_id"], "verified": True,
            "status": decision["status"], "reason_code": decision["reason_code"],
            "late_seconds": decision.get("late_seconds"),
            "proposed_coupon_yuan": decision.get("proposed_coupon_yuan"),
            "ticket_id": ticket["ticket_id"] if ticket and ticket["customer_id"] == customer_id else None,
        }

    def claim_goodwill_care(self, customer_id: str, order_id: str) -> dict:
        """Self-service 1-click ¥3 platform goodwill care coupon for 15–30m near-threshold delays (0 CPT human cost)."""
        _, order = self.data.lookup_for_customer(normalize_order_id(order_id), customer_id)
        if order is None:
            raise ServiceError(404, "order_not_found", "当前账号下没有这笔订单。")
        sub = compute_actuarial_subrogation(order, self.policy)
        care_yuan = int(sub.get("goodwill_care_yuan") or 0)
        if care_yuan <= 0:
            raise ServiceError(409, "goodwill_not_applicable", "该订单不在临界延迟关怀区间内。")
        tenant_id = str(order.get("tenant_id") or "M_67REST")
        grant, created = self.store.claim_goodwill(
            customer_id=customer_id, order_id=order["order_id"], tenant_id=tenant_id,
            amount_yuan=care_yuan, reason="临界延迟平台体验金秒发关怀券",
        )
        self._record(
            event="goodwill_claimed", customer_id=customer_id, order_id=order["order_id"],
            outcome="granted" if created else "reused", amount_yuan=care_yuan,
        )
        return {"grant": grant, "created": created}

    async def stream_message(self, thread_id: str, customer_id: str, text: str):
        """True async LangGraph astream with per-thread async lock, punctuation clause buffering & reply_risk guard."""
        async with self._async_lock(thread_id):
            snapshot = self.customer_graph.get_state(self._thread(thread_id))
            pending_confirm = first_request(snapshot.interrupts, "confirm_submission")
            if wants_person(text):
                if pending_confirm:
                    await self.customer_graph.ainvoke(Command(resume="cancel"), self._thread(thread_id), context=CustomerContext(customer_id))
                    snapshot = self.customer_graph.get_state(self._thread(thread_id))
                res = self._open_handoff(thread_id, customer_id, text, snapshot)
                yield {"type": "done", "result": {"outcome": "handoff_requested" if res["created"] else "handoff_waiting",
                                                 "reason_code": None, "messages": [], "confirmation": None, "ticket": None, **res}}
                return
            if pending_confirm and SPECIAL_ISSUE_RE.search(text):
                await self.customer_graph.ainvoke(Command(resume="cancel"), self._thread(thread_id), context=CustomerContext(customer_id))
                snapshot = self.customer_graph.get_state(self._thread(thread_id))
                pending_confirm = None
            if pending_confirm:
                raise ServiceError(409, "confirmation_pending", "请先确认或取消当前的提交。")

            config = self._thread(thread_id)
            before = len((snapshot.values or {}).get("messages", []))
            started = time.perf_counter()
            clause_buf = ""
            emitted_len = 0
            retracted = False
            final_values = None
            cust_prices = {float(o["amount_yuan"]) for o in self.data.orders_for_customer(customer_id) if o.get("amount_yuan")}
            existing_statuses = {t["status"] for t in self.store.tickets(customer_id=customer_id)} | {"pending"}
            allowed = {float(self.policy.coupon_yuan)} | {
                round(min(float(self.policy.coupon_yuan), max(2.0, p * 0.40)), 1) for p in cust_prices
            }

            yield {"type": "ack", "status": "verifying"}
            try:
                async for mode, chunk in self.customer_graph.astream(
                    {"messages": [HumanMessage(content=text)]},
                    config,
                    context=CustomerContext(customer_id),
                    stream_mode=["messages", "values"],
                ):
                    if mode == "messages":
                        msg_chunk, meta = chunk
                        node_name = (meta or {}).get("langgraph_node", "")
                        if node_name in ("agent", "assess") and getattr(msg_chunk, "content", None) and not getattr(msg_chunk, "tool_calls", None):
                            piece = str(msg_chunk.content)
                            clause_buf += piece
                            if not retracted and any(p in piece for p in ("，", "。", "！", "？", "；", "\n")):
                                risk = reply_risk(clause_buf, allowed_amounts=allowed, statuses=existing_statuses, order_prices=cust_prices)
                                if risk is not None:
                                    retracted = True
                                    yield {"type": "replace", "text": GUARDED_REPLY}
                                elif len(clause_buf) > emitted_len:
                                    delta = clause_buf[emitted_len:]
                                    emitted_len = len(clause_buf)
                                    yield {"type": "delta", "text": delta}
                    elif mode == "values":
                        final_values = chunk
            except APIStatusError as exc:
                self._record(event="model_error", outcome="provider_error", http_status=exc.status_code)
                raise ServiceError(503, "model_unavailable", "客服暂时无法连接，请稍后重试。你的输入已保留。") from None
            except APIConnectionError:
                self._record(event="model_error", outcome="connection_error")
                raise ServiceError(503, "model_unavailable", "客服连接超时或中断，请重试。你的输入已保留。") from None

            result = final_values or (self.customer_graph.get_state(config).values or {})
            end_snap = self.customer_graph.get_state(config)
            latency_ms = round((time.perf_counter() - started) * 1000)
            new_messages = result.get("messages", [])[before:]
            ticket = self.store.get(result["ticket_id"]) if result.get("ticket_id") else None
            if result.get("outcome") == "ticket_created":
                self._open_review(ticket["ticket_id"])
            confirmation = first_request(end_snap.interrupts, "confirm_submission")
            vis = visible_messages(new_messages)
            assistant_vis = [m for m in vis if m["role"] == "assistant"]
            if assistant_vis:
                final_txt = assistant_vis[-1]["text"]
                if retracted or not final_txt.startswith(clause_buf[:emitted_len]):
                    yield {"type": "replace", "text": final_txt}
                elif len(final_txt) > emitted_len:
                    yield {"type": "delta", "text": final_txt[emitted_len:]}
            order_id = requested_order(new_messages) or (confirmation or ticket or {}).get("order_id")
            self._record(event="customer_message_stream", customer_id=customer_id, thread_id=thread_id,
                         outcome=result.get("outcome"), reason_code=result.get("reason_code"),
                         order_id=order_id, ticket_id=ticket["ticket_id"] if ticket else None,
                         latency_ms=latency_ms, usage=token_usage(new_messages))
            yield {
                "type": "done",
                "result": {
                    "outcome": result.get("outcome"),
                    "reason_code": result.get("reason_code"),
                    "messages": vis,
                    "confirmation": confirmation,
                    "ticket": customer_copy(ticket) if ticket else None,
                },
            }

    def send_message(self, thread_id: str, customer_id: str, text: str) -> dict:
        with self._lock(thread_id):
            snapshot = self.customer_graph.get_state(self._thread(thread_id))
            pending_confirm = first_request(snapshot.interrupts, "confirm_submission")
            # Emergency human-handoff & P0 food-safety escape hatches ALWAYS work, even if a confirmation card was open!
            if wants_person(text):
                if pending_confirm:
                    self._run(thread_id, customer_id, Command(resume="cancel"), "customer_cancel", snapshot)
                    snapshot = self.customer_graph.get_state(self._thread(thread_id))
                result = self._open_handoff(thread_id, customer_id, text, snapshot)
                return {"outcome": "handoff_requested" if result["created"] else "handoff_waiting",
                        "reason_code": None, "messages": [], "confirmation": None, "ticket": None, **result}
            if pending_confirm and SPECIAL_ISSUE_RE.search(text):
                self._run(thread_id, customer_id, Command(resume="cancel"), "customer_cancel", snapshot)
                snapshot = self.customer_graph.get_state(self._thread(thread_id))
                pending_confirm = None
            if pending_confirm:
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
        guarded = {"guarded": result.get("guarded")} if result.get("reason_code") == "reply_guarded" else {}
        self._record(event=event, customer_id=customer_id, thread_id=thread_id, outcome=result.get("outcome"),
                     reason_code=result.get("reason_code"), order_id=order_id,
                     ticket_id=ticket["ticket_id"] if ticket else None,
                     latency_ms=latency_ms, usage=token_usage(new_messages), **guarded)
        return {
            "outcome": result.get("outcome"),
            "reason_code": result.get("reason_code"),
            "messages": visible_messages(new_messages),
            "confirmation": confirmation,
            "ticket": customer_copy(ticket) if ticket else None,
        }

    def customer_orders(self, customer_id: str) -> list[dict]:
        return [customer_order_copy(o) for o in self.data.orders_for_customer(customer_id)]

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

    def rate_ticket(self, customer_id: str, ticket_id: str, rating) -> dict:
        if isinstance(rating, bool) or not isinstance(rating, int) or not 1 <= rating <= 5:
            raise ServiceError(400, "invalid_rating", "评分须为 1 到 5 的整数。")
        ticket = self.store.get(ticket_id)
        if ticket is None or ticket["customer_id"] != customer_id:
            raise ServiceError(404, "ticket_not_found", "当前账号下没有这张工单。")
        if ticket["status"] not in ("approved", "rejected"):
            raise ServiceError(409, "ticket_not_decided", "审核完成后才能评价。")
        if self.store.rate(ticket_id, customer_id=customer_id, rating=rating) is None:
            raise ServiceError(409, "already_rated", "这份申请已经评价过。")
        self._record(event="customer_rating", customer_id=customer_id, outcome="rated", rating=rating,
                     order_id=ticket["order_id"], ticket_id=ticket_id)
        return self.customer_ticket(customer_id, ticket_id)

    # Human handoff (non-blocking snapshot read so emergency escape button never hangs behind slow LLM calls)

    def request_handoff(self, thread_id: str, customer_id: str, text: str | None = None,
                        files: list[dict] | None = None) -> dict:
        snapshot = self.customer_graph.get_state(self._thread(thread_id))
        return self._open_handoff(thread_id, customer_id, text, snapshot, files or [])

    def _open_handoff(self, thread_id: str, customer_id: str, text: str | None, snapshot,
                      files: list[dict] | None = None) -> dict:
        messages = (snapshot.values or {}).get("messages", [])
        visible = visible_messages(messages)
        confirmation = first_request(snapshot.interrupts, "confirm_submission")
        named = ORDER_ID.findall(text or "")
        candidate = (normalize_order_id(named[-1]) if named else None) or (confirmation or {}).get("order_id") \
            or focused_order(messages)
        focus = self._focus(customer_id, candidate)
        order_id = focus["order_id"] if focus and focus["verified"] else None
        excerpt = [{"role": item["role"], "text": item["text"].replace("查单工具 query_order：", "查询 ")[:EXCERPT_CHARS]}
                   for item in visible[-EXCERPT_LINES:]]
        order_obj = self.data.orders.get(order_id or "") or {}
        tenant_id = str(order_obj.get("tenant_id") or "M_67REST")
        try:
            handoff, created = self.store.create_handoff(
                customer_id=customer_id, thread_id=thread_id, order_id=order_id, after_index=len(visible),
                request_text=text, excerpt=excerpt, files=files or [], limit=HANDOFF_LIMIT, tenant_id=tenant_id)
        except ValueError as exc:
            if "attachment_quota_exceeded" in str(exc):
                raise ServiceError(409, "attachment_limit", "单次人工咨询最多上传 3 个附件。") from None
            if "customer_disk_quota_exceeded" in str(exc):
                raise ServiceError(413, "customer_quota_exceeded", "当前账号累计上传凭证容量已达上限（25 MB）。") from None
            raise
        if handoff is None:
            raise ServiceError(429, "handoff_limit", "当前人工排队人数已满，请稍后再试。")
        self._record(event="handoff_request", customer_id=customer_id, thread_id=thread_id,
                     outcome="waiting" if created else "already_waiting", order_id=order_id,
                     handoff_id=handoff["handoff_id"], via="keyword" if text else "button")
        return {"handoff": handoff_copy(handoff, thread_id), "created": created}

    def cancel_handoff(self, thread_id: str, customer_id: str, handoff_id: str) -> dict:
        handoff = self.store.close_handoff(handoff_id, status="cancelled", customer_id=customer_id)
        if handoff is None:
            current = self.store.get_handoff(handoff_id)
            if current is None or current["customer_id"] != customer_id:
                raise ServiceError(404, "handoff_not_found", "当前账号下没有这条人工咨询。")
            raise ServiceError(409, "handoff_closed", "这条人工咨询已经结束。")
        self._record(event="handoff_cancel", customer_id=customer_id, outcome="cancelled",
                     order_id=handoff["order_id"], handoff_id=handoff_id)
        return {"handoff": handoff_copy(handoff, thread_id)}

    def customer_handoff_followup(self, thread_id: str, customer_id: str, handoff_id: str, text: str) -> dict:
        """Allow customer to send a two-way reply back to the human specialist on an active/replied handoff."""
        if not isinstance(text, str) or not text.strip():
            raise ServiceError(400, "invalid_text", "请填写追加留言内容。")
        text = text.strip()
        if len(text) > REPLY_LIMIT:
            raise ServiceError(400, "text_too_long", f"留言不能超过 {REPLY_LIMIT} 个字。")
        updated = self.store.append_handoff_followup(
            handoff_id, sender_role="customer", sender_id=customer_id, text=text, customer_id=customer_id
        )
        if updated is None:
            raise ServiceError(404, "handoff_not_found", "当前账号下没有这条人工咨询或已取消。")
        self._record(event="customer_handoff_followup", customer_id=customer_id, outcome="customer_followup_sent",
                     order_id=updated["order_id"], handoff_id=handoff_id)
        return {"handoff": handoff_copy(updated, thread_id)}

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

    def _enrich_review_ticket(self, ticket: dict) -> dict:
        order = self.data.orders.get(ticket["order_id"], {})
        subrogation = compute_actuarial_subrogation(order, self.policy)
        extra = {key: order.get(key) for key in (
            "amount_yuan", "ordered_at", "prep_promised_at", "prep_done_at",
            "picked_up_at", "liability_party", "liability_detail",
            "rider_protection", "gps_fence_note", "items"
        ) if key in order}
        order_files = [
            {**att, "url": f"/api/media/{att['attachment_id']}"}
            for att in self.store.attachments_for_order(ticket["order_id"], ticket["customer_id"])
        ]
        clean_ticket = {
            k: v for k, v in ticket.items()
            if not (k in ("stp_tier", "merchant_bear_yuan", "platform_bear_yuan", "tenant_id") and v is None)
        }
        return {**extra, **subrogation, "order_attachments": order_files, **clean_ticket}

    def review_tickets(self, reviewer_id: str | None = None) -> dict:
        tenant_id = self._reviewer_tenant(reviewer_id)
        with self._review_lock:
            tickets = [self._enrich_review_ticket(ticket) for ticket in self.store.tickets(tenant_id=tenant_id)]
            return {
                "stp_auto_approve": self.stp_auto_approve,
                "tenant_id": tenant_id or "M_67REST",
                "pending": [{**ticket, "review_request": self._open_review(ticket["ticket_id"])
                             if ticket["status"] == "pending" else None}
                            for ticket in tickets if ticket["status"] in ("pending", "needs_info")],
                "decided": [ticket for ticket in tickets if ticket["status"] in ("approved", "rejected")],
            }

    def batch_approve_green_stp(self, reviewer_id: str) -> dict:
        """One-click subrogation approval for all pending pure-logistics-delay (merchant ¥0) tickets."""
        if reviewer_id not in self.data.reviewers:
            raise ServiceError(403, "not_a_reviewer", "当前身份没有审批权限。")
        tenant_id = self._reviewer_tenant(reviewer_id)
        approved_ids: list[str] = []
        for raw_ticket in self.store.tickets(tenant_id=tenant_id):
            if raw_ticket["status"] != "pending":
                continue
            enriched = self._enrich_review_ticket(raw_ticket)
            if enriched.get("stp_tier") == "STP_L1_GREEN" or enriched.get("merchant_bear_yuan") == 0:
                note = "平台准时保池 100% 直赔（本店按时出餐 ¥0 承担）"
                self.decide(raw_ticket["ticket_id"], reviewer_id, "approve", note)
                approved_ids.append(raw_ticket["ticket_id"])
        return {"approved_ticket_ids": approved_ids, "count": len(approved_ids)}

    def analytics(self, reviewer_id: str | None = None) -> dict:
        """Real-time Unit Economics, Subrogation Recovery, Guardrail & CSAT Flywheel dashboard for /review."""
        tenant_id = self._reviewer_tenant(reviewer_id)
        tickets = [self._enrich_review_ticket(t) for t in self.store.tickets(tenant_id=tenant_id)]
        handoffs = self.store.handoffs(tenant_id=tenant_id)
        goodwills = self.store.goodwill_grants(tenant_id=tenant_id)
        approved = [t for t in tickets if t["status"] == "approved"]
        goodwill_yuan = round(sum(float(g.get("amount_yuan") or 0) for g in goodwills), 1)
        platform_pool_yuan = round(sum(float(t.get("platform_bear_yuan") or 0) for t in approved) + goodwill_yuan, 1)
        merchant_bear_yuan = round(sum(float(t.get("merchant_bear_yuan") or 0) for t in approved), 1)
        stp_green_count = sum(1 for t in tickets if t.get("stp_tier") == "STP_L1_GREEN")
        ratings = [t["rating"] for t in tickets if t.get("rating") is not None]
        guarded_hits = sum(1 for r in self.run_log if r.get("reason_code") == "reply_guarded")
        dup_alerts = sum(
            1 for h in handoffs for a in h.get("attachments", []) if a.get("duplicate_alert")
        )
        chain_status = self.store.verify_audit_chain()
        return {
            "tenant_id": tenant_id or "M_67REST",
            "total_tickets": len(tickets),
            "stp_green_eligible": stp_green_count,
            "goodwill_grants_count": len(goodwills),
            "goodwill_issued_yuan": goodwill_yuan,
            "platform_subrogation_saved_yuan": platform_pool_yuan,
            "merchant_net_cost_yuan": merchant_bear_yuan,
            "avg_csat": round(sum(ratings) / len(ratings), 2) if ratings else None,
            "guardrail_intercepts": guarded_hits,
            "duplicate_evidence_alerts": dup_alerts,
            "estimated_agent_yuan_saved": round((len(tickets) + len(goodwills)) * 6.5, 1),
            "audit_chain_intact": chain_status["intact"],
            "audit_entries": chain_status["entries"],
        }

    def runs(self, limit: int = 100) -> list[dict]:
        return list(self.run_log)[-limit:]

    def review_handoffs(self, reviewer_id: str | None = None) -> dict:
        tenant_id = self._reviewer_tenant(reviewer_id)
        items = [
            review_handoff_copy(item, self.data.orders.get(item.get("order_id") or ""))
            for item in self.store.handoffs(tenant_id=tenant_id)
        ]
        for item in items:
            item["attachments"] = [{**attachment, "url": f"/api/media/{attachment['attachment_id']}"}
                                    for attachment in item.get("attachments", [])]
        waiting = sorted(items, key=lambda x: (0 if x.get("priority") == "P0_FOOD_SAFETY" else 1, x["handoff_id"]))
        return {
            "waiting": [item for item in waiting if item["status"] == "waiting"],
            "closed": [item for item in items if item["status"] != "waiting"][-50:],
        }

    def media_for(self, attachment_id: str, *, customer_id: str | None = None,
                  reviewer: bool = False, reviewer_id: str | None = None) -> dict:
        attachment = self.store.attachment(attachment_id)
        if attachment is None:
            raise ServiceError(404, "media_not_found", "没有这个附件。")
        handoff = self.store.get_handoff(attachment["handoff_id"])
        if handoff is None or (not reviewer and handoff["customer_id"] != customer_id):
            raise ServiceError(404, "media_not_found", "没有这个附件。")
        if reviewer and reviewer_id:
            self._assert_tenant_access(reviewer_id, handoff.get("tenant_id"))
        path = self.store.media_dir / attachment["storage_name"]
        if not path.is_file():
            raise ServiceError(404, "media_not_found", "附件文件已不存在。")
        return {"path": path, "media_type": attachment["media_type"], "name": attachment["original_name"]}

    def reply_handoff(self, handoff_id: str, reviewer_id: str, text) -> dict:
        if not isinstance(text, str) or not text.strip():
            raise ServiceError(400, "invalid_text", "请填写回复内容。")
        text = text.strip()
        if len(text) > REPLY_LIMIT:
            raise ServiceError(400, "text_too_long", f"回复不能超过 {REPLY_LIMIT} 个字。")
        if reviewer_id not in self.data.reviewers:
            raise ServiceError(403, "not_a_reviewer", "当前身份没有处理权限。")
        existing_h = self.store.get_handoff(handoff_id)
        if existing_h is None:
            raise ServiceError(404, "handoff_not_found", "没有这条人工咨询。")
        self._assert_tenant_access(reviewer_id, existing_h.get("tenant_id"))
        started = time.perf_counter()
        handoff = self.store.close_handoff(handoff_id, status="replied", reviewer_id=reviewer_id, reply_text=text)
        if handoff is None:
            raise ServiceError(409, "handoff_closed", "顾客已取消，或这条咨询已经回复。")
        self._record(event="handoff_reply", reviewer_id=reviewer_id, customer_id=handoff["customer_id"],
                     outcome="replied", order_id=handoff["order_id"], handoff_id=handoff_id,
                     latency_ms=round((time.perf_counter() - started) * 1000))
        return {"handoff": review_handoff_copy(handoff, self.data.orders.get(handoff.get("order_id") or ""))}

    def followup_handoff(self, handoff_id: str, reviewer_id: str, text) -> dict:
        """Send an additional follow-up message on an already-replied handoff (eliminates 1-message lockout)."""
        if not isinstance(text, str) or not text.strip():
            raise ServiceError(400, "invalid_text", "请填写追回内容。")
        text = text.strip()
        if len(text) > REPLY_LIMIT:
            raise ServiceError(400, "text_too_long", f"回复不能超过 {REPLY_LIMIT} 个字。")
        if reviewer_id not in self.data.reviewers:
            raise ServiceError(403, "not_a_reviewer", "当前身份没有处理权限。")
        existing_h = self.store.get_handoff(handoff_id)
        if existing_h is None:
            raise ServiceError(404, "handoff_not_found", "没有这条人工咨询或顾客已取消。")
        self._assert_tenant_access(reviewer_id, existing_h.get("tenant_id"))
        updated = self.store.append_handoff_followup(handoff_id, sender_role="reviewer", sender_id=reviewer_id, text=text)
        if updated is None:
            raise ServiceError(404, "handoff_not_found", "没有这条人工咨询或顾客已取消。")
        self._record(event="handoff_followup", reviewer_id=reviewer_id, customer_id=updated["customer_id"],
                     outcome="followup_sent", order_id=updated["order_id"], handoff_id=handoff_id)
        return {"handoff": review_handoff_copy(updated, self.data.orders.get(updated.get("order_id") or ""))}

    def review_detail(self, ticket_id: str, reviewer_id: str | None = None) -> dict:
        raw = self._ticket_or_404(ticket_id)
        self._assert_tenant_access(reviewer_id, raw.get("tenant_id"))
        ticket = self._enrich_review_ticket(raw)
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
            self._assert_tenant_access(reviewer_id, current.get("tenant_id"))
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
        return {"ticket": self._enrich_review_ticket(ticket), "events": self.store.events(ticket_id)}

    def reset(self) -> None:
        """Clear demo tickets, handoffs and conversations (blocked in prod/legal-hold; audit_logs stays append-only)."""
        if os.getenv("ORD001_PRODUCTION_MODE") == "1" or os.getenv("ORD001_LEGAL_HOLD") == "1":
            raise ServiceError(403, "reset_disabled_in_prod", "生产合规与诉讼保全模式下禁止物理清空客诉存证数据。")
        with self._review_lock, self._guard:
            archived_hashes = self.store.reset()
            self._thread_locks.clear()
            self._async_thread_locks.clear()
            self.run_log.clear()
            self._build_graphs()
        self._record(event="reset", archived_media_sha256_prefixes=archived_hashes)
