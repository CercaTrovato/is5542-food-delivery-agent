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
SECOND_APPEAL_RE = re.compile(r"二次申请|再次申请|重新申请|继续申请|申请复核|人工复核|复议|申诉|不服驳回|对驳回有疑问")
BARE_HANDOFF = re.compile(r"\s*(?:转)?人工(?:客服|服务)?[\s!！。.~～]*")
EXPLICIT_NO_HANDOFF_RE = re.compile(
    r"(?:不用|不要|无需|不必|先不|别|不找|不转|不需要)\s*(?:帮我|给我|替我)?\s*(?:转接?|找|联系)?\s*(?:人工|真人|活人|客服|专员)"
)
LOCAL_NEGATION_RE = re.compile(
    r"(?:不是要|并非|不是|不要|不用|无需|不必|先不|不找|不转|不需要|别(?!废话|啰嗦|磨叽|扯))[^，。！？；,.!?;\n]{0,4}$"
)
QUESTION_FORMS = ("能不能", "可不可以", "可以不可以", "是不是", "要不要")
HANDOFF_LIMIT, HANDOFF_SHOWN = 500, 20
EXCERPT_LINES, EXCERPT_CHARS = 6, 160
REPLY_LIMIT = 500
MAX_LOCK_ENTRIES = 512


class ServiceError(Exception):
    """An expected refusal that the web layer turns into an HTTP status."""

    def __init__(self, status: int, code: str, message: str, *, extra: dict | None = None):
        super().__init__(message)
        self.status, self.code, self.message, self.extra = status, code, message, (extra or {})


REVIEW_POLICY_VERSION = "human-review-v1"
VALID_RECONSIDER_REASONS = ("verifiable_relevant_new_information", "prior_processing_error")


def build_model_bundle(config_path=None):
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
        thinking_mode = "default"
        if base.hostname == "api.deepseek.com":
            options["extra_body"] = {"thinking": {"type": "disabled"}}
            thinking_mode = "disabled"
        redacted_params = {
            "provider": "openai_compatible",
            "requested_model": options["model"],
            "base_url": options["base_url"],
            "temperature": options["temperature"],
            "max_tokens": options["max_tokens"],
            "timeout_seconds": options["timeout"],
            "max_retries": options["max_retries"],
            "thinking": thinking_mode,
        }
        return init_chat_model(**options), f"openai:{options['model']}", redacted_params
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
        redacted_params = {
            "provider": "openai_compatible",
            "requested_model": model_name,
            "base_url": base_url,
            "temperature": 0.35,
            "max_tokens": 800,
            "timeout_seconds": 30,
            "max_retries": 0,
            "thinking": "disabled",
        }
        return init_chat_model(**options), f"openai:{model_name}", redacted_params
    model_id = os.getenv("ORD001_CHAT_MODEL")
    if model_id:
        return init_chat_model(model_id, timeout=30, max_retries=0), model_id, {
            "provider": "langchain_init_chat_model",
            "requested_model": model_id,
            "timeout_seconds": 30,
            "max_retries": 0,
        }
    return ScriptedOrderModel(), "ord001-scripted-model", {
        "provider": "local_scripted_mock",
        "requested_model": "ord001-scripted-model",
    }


def default_model(config_path=None):
    model, label, _ = build_model_bundle(config_path)
    return model, label


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


def last_verified_order(messages, customer_id: str, data: DemoData) -> str | None:
    """Walk full conversation history backward to find the latest verified order belonging to this customer."""
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            for raw in reversed(ORDER_ID.findall(message.text)):
                cand = normalize_order_id(raw)
                if data.lookup_for_customer(cand, customer_id)[1] is not None:
                    return cand
        elif isinstance(message, AIMessage):
            for call in reversed(message.tool_calls):
                raw_oid = call["args"].get("order_id")
                if isinstance(raw_oid, str) and raw_oid.strip():
                    cand = normalize_order_id(raw_oid)[:32]
                    if data.lookup_for_customer(cand, customer_id)[1] is not None:
                        return cand
    return None


def extract_initial_appeal(visible: list[dict], order_id: str | None, request_text: str | None) -> str | None:
    """Extract the customer's opening appeal for the consulted order even after many follow-up turns."""
    if order_id:
        for idx, item in enumerate(visible):
            if item["role"] == "customer":
                in_text = any(normalize_order_id(m) == order_id for m in ORDER_ID.findall(item["text"]))
                next_is_tool = (
                    idx + 1 < len(visible)
                    and visible[idx + 1]["role"] == "tool"
                    and order_id in visible[idx + 1]["text"]
                )
                if in_text or next_is_tool:
                    return item["text"][:EXCERPT_CHARS]
    for item in visible:
        if item["role"] == "customer" and item["text"].strip():
            return item["text"][:EXCERPT_CHARS]
    return request_text.strip()[:EXCERPT_CHARS] if request_text and request_text.strip() else None


def build_handoff_excerpt(visible: list[dict], order_id: str | None) -> list[dict]:
    """Preserve BOTH the opening order consultation and recent multi-turn context for the merchant."""
    formatted = [
        {"role": item["role"], "text": item["text"].replace("查单工具 query_order：", "查询 ")[:EXCERPT_CHARS]}
        for item in visible
    ]
    if len(formatted) <= 12:
        return formatted
    start_idx = 0
    if order_id:
        for idx, item in enumerate(visible):
            if item["role"] == "customer":
                if any(normalize_order_id(m) == order_id for m in ORDER_ID.findall(item["text"])):
                    start_idx = idx
                    break
            elif item["role"] == "tool" and order_id in item["text"]:
                start_idx = max(0, idx - 1)
                break
    head_end = min(len(formatted) - 8, start_idx + 4)
    if head_end <= start_idx:
        return formatted[-12:]
    head = formatted[start_idx:head_end]
    tail = formatted[-8:]
    omitted = (len(formatted) - 8) - head_end
    marker = [{"role": "tool", "text": f"… 中间省略 {omitted} 条历史消息 …"}] if omitted > 0 else []
    return head + marker + tail


def handoff_copy(handoff: dict, thread_id: str | None) -> dict:
    """What the customer sees of a handoff, including chronologically anchored chat events."""
    keys = ("handoff_id", "order_id", "status", "request_text", "reply_text", "created_at", "closed_at")
    attachments = [{**item, "url": f"/api/media/{item['attachment_id']}"} for item in handoff.get("attachments", [])]
    same_thread = handoff["thread_id"] == thread_id
    base_after = handoff["after_index"] if same_thread else 0
    rep_after = (
        handoff["reply_after_index"]
        if same_thread and handoff.get("reply_after_index") is not None
        else base_after
    )
    followups_raw = handoff.get("followups") or []
    reply_seq = handoff.get("reply_seq")
    open_attachments = [a for a in attachments if not a.get("is_followup")]
    followup_atts = [a for a in attachments if a.get("is_followup")]
    msg_ids = {f.get("message_id") for f in followups_raw if f.get("message_id")}
    by_msg: dict[int, list[dict]] = {}
    loose_atts: list[dict] = []
    for att in followup_atts:
        seq = att.get("followup_seq")
        if seq and seq in msg_ids:
            by_msg.setdefault(seq, []).append(att)
        else:
            loose_atts.append(att)

    events: list[dict] = [{"kind": "open", "after": base_after, "at": handoff["created_at"]}]

    def emit_followup(f: dict, default_after: int) -> None:
        f_after = (f["after_index"] if f.get("after_index") is not None else default_after) if same_thread else 0
        events.append({
            "kind": "message",
            "role": "customer" if f["sender_role"] == "customer" else ("system" if f["sender_role"] == "system" else "human"),
            "text": f["text"],
            "after": f_after,
            "at": f["created_at"],
        })
        linked = by_msg.get(f.get("message_id") or -1)
        if linked:
            events.append({"kind": "attachment", "attachments": linked, "after": f_after, "at": linked[-1]["created_at"]})

    if handoff["status"] == "replied" and handoff.get("reply_text"):
        pre_f = [
            f for f in followups_raw
            if (reply_seq is not None and f.get("message_id", 0) <= reply_seq)
            or (reply_seq is None and f["created_at"] < (handoff.get("closed_at") or ""))
        ]
        pre_ids = {id(f) for f in pre_f}
        post_f = [f for f in followups_raw if id(f) not in pre_ids]
        for f in pre_f:
            emit_followup(f, base_after)
        events.append({
            "kind": "message",
            "role": "human",
            "text": handoff["reply_text"],
            "after": rep_after,
            "at": handoff.get("closed_at") or handoff["created_at"],
        })
        for f in post_f:
            emit_followup(f, rep_after)
    else:
        for f in followups_raw:
            emit_followup(f, base_after)

    for att in loose_atts:
        a_after = (att["after_index"] if same_thread and att.get("after_index") is not None
                   else (rep_after if handoff["status"] == "replied" else base_after))
        events.append({"kind": "attachment", "attachments": [att], "after": a_after, "at": att["created_at"]})

    res = {
        **{key: handoff[key] for key in keys},
        "ended_at": handoff.get("ended_at"),
        "attachments": attachments,
        "open_attachments": open_attachments,
        "after": base_after,
        "events": events,
    }
    if followups_raw:
        res["followups"] = [{"sender_role": f["sender_role"], "text": f["text"], "created_at": f["created_at"]}
                            for f in followups_raw]
    return res


def review_handoff_copy(handoff: dict, order: dict | None = None, related_ticket: dict | None = None) -> dict:
    result = {key: value for key, value in handoff.items() if key not in ("thread_id", "attachments")}
    result["attachments"] = [
        {
            **{key: item[key] for key in ("attachment_id", "handoff_id", "kind", "original_name", "media_type", "size_bytes", "created_at")},
            **({"forensic_note": item["forensic_note"], "duplicate_alert": item.get("duplicate_alert", False)}
               if "forensic_note" in item else {}),
        }
        for item in handoff.get("attachments", [])
    ]
    excerpt_list = handoff.get("excerpt") or []
    if not result.get("initial_appeal"):
        first_cust = next((x["text"] for x in excerpt_list if x.get("role") == "customer" and x.get("text")), None)
        result["initial_appeal"] = first_cust or handoff.get("request_text")
    followups = handoff.get("followups") or []
    result["needs_specialist_reply"] = bool(
        handoff.get("status") == "replied"
        and not handoff.get("ended_at")
        and followups
        and followups[-1].get("sender_role") == "customer"
    )
    req_txt = str(handoff.get("request_text") or "") + " " + str(result.get("initial_appeal") or "")
    excerpt_txt = " ".join(x.get("text", "") for x in excerpt_list)
    fup_txt = " ".join(x.get("text", "") for x in followups)
    is_food_p0 = bool(SPECIAL_ISSUE_RE.search(f"{req_txt} {excerpt_txt} {fup_txt}"))
    result["priority"] = "P0_FOOD_SAFETY" if is_food_p0 else ("P1_EVIDENCE" if result["attachments"] else "NORMAL")
    if order:
        result["order_summary"] = {
            k: order.get(k) for k in (
                "merchant", "amount_yuan", "status", "ordered_at", "prep_promised_at",
                "prep_done_at", "picked_up_at", "expected_at", "delivered_at",
                "liability_party", "liability_detail", "rider_protection", "gps_fence_note", "items"
            ) if k in order
        }
    if related_ticket:
        result["related_ticket"] = {
            k: related_ticket.get(k)
            for k in (
                "ticket_id", "status", "review_note", "prior_review_note", "proposed_coupon_yuan", "coupon_issued_yuan",
                "information_request", "customer_information", "is_expedited", "escalated_to", "assigned_reviewer_id"
            )
        }
    return result


def token_usage(messages) -> dict | None:
    total = {}
    for message in messages:
        for key, value in (getattr(message, "usage_metadata", None) or {}).items():
            if isinstance(value, int):
                total[key] = total.get(key, 0) + value
    return total or None


def extract_returned_model(messages) -> tuple[str | None, int]:
    """Return (provider_returned_model_id, llm_call_count) from AIMessage metadata."""
    ret_model = None
    calls = 0
    for message in messages:
        if isinstance(message, AIMessage):
            meta = getattr(message, "response_metadata", None) or {}
            usage = getattr(message, "usage_metadata", None)
            if meta or usage:
                calls += 1
            cand = meta.get("model_name") or meta.get("model")
            if isinstance(cand, str) and cand.strip():
                ret_model = cand.strip()
    return ret_model, calls


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
                 data=None, policy=None, db_path=":memory:", stp_auto_approve: bool = False,
                 agent_mode: str | None = None):
        if model is None:
            model, model_label, model_params = build_model_bundle(model_config_path)
        else:
            model_params = {"provider": "injected_model", "requested_model": model_label or type(model).__name__}
        self.model = model
        self.model_label = model_label or getattr(model, "_llm_type", type(model).__name__)
        self.model_params = model_params
        self.last_returned_model: str | None = None
        mode_raw = (agent_mode or os.getenv("ORD001_AGENT_MODE") or "C").strip().upper()
        if mode_raw not in ("C", "B"):
            raise ValueError("agent_mode 仅支持 'C'（显式业务规则型）或 'B'（基础工具型对照）。")
        self.agent_mode = mode_raw
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
            agent_mode=self.agent_mode,
        )
        self.review_graph = build_review_graph(self.store, checkpointer=self._review_ckpt)

    def info(self) -> dict:
        return {
            "policy": asdict(self.policy),
            "review_policy_version": REVIEW_POLICY_VERSION,
            "agent_mode": self.agent_mode,
            "stp_auto_approve": self.stp_auto_approve,
            "data_version": self.data.version,
            "service_date": self.data.service_date,
            "model": self.model_label,
            "model_params": self.model_params,
            "last_returned_model": self.last_returned_model,
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

    def _assert_action_permission(self, reviewer_id: str, permission: str | None = None) -> dict:
        rev = self.data.reviewers.get(reviewer_id)
        if rev is None:
            raise ServiceError(403, "not_a_reviewer", "当前身份没有处理权限。")
        if rev.get("can_handle") is False or rev.get("role") == "observer":
            raise ServiceError(403, "permission_denied", "当前坐席角色为只读观察权限，无权执行业务处理操作。")
        perms = rev.get("permissions")
        if permission and isinstance(perms, list) and permission not in perms:
            raise ServiceError(403, "permission_denied", f"当前坐席角色缺少 {permission} 操作权限。")
        return rev

    def set_stp_mode(self, enabled: bool, reviewer_id: str) -> dict:
        self._assert_action_permission(reviewer_id, "ticket_approve")
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
        entry = {
            "at": now_text(), **entry,
            "policy_version": self.policy.version,
            "review_policy_version": REVIEW_POLICY_VERSION,
            "agent_mode": self.agent_mode,
            "model": self.model_label,
        }
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

    def _visible_len(self, thread_id: str) -> int:
        if not thread_id:
            return 0
        snap = self.customer_graph.get_state(self._thread(thread_id))
        return len(visible_messages((snap.values or {}).get("messages", [])))

    def customer_view(self, thread_id: str, customer_id: str) -> dict:
        snapshot = self.customer_graph.get_state(self._thread(thread_id))
        messages = (snapshot.values or {}).get("messages", [])
        visible = visible_messages(messages)
        confirmation = first_request(snapshot.interrupts, "confirm_submission")
        handoffs = self.store.handoffs(customer_id=customer_id)
        active_list = self.store.active_handoffs(customer_id, thread_id)
        active = self.store.active_handoff(customer_id, thread_id)
        own = [item for item in handoffs if item["thread_id"] == thread_id]
        handoff_order = (
            active["order_id"]
            if active and active.get("order_id") and active["after_index"] >= len(visible)
            else (own[-1]["order_id"] if own and own[-1]["after_index"] >= len(visible) else None)
        )
        order_id = (confirmation or {}).get("order_id") or handoff_order or focused_order(messages)
        return {
            "messages": visible,
            "confirmation": confirmation,
            "tickets": self.customer_tickets(customer_id),
            "goodwill_grants": self.store.goodwill_grants(customer_id=customer_id),
            "focus": self._focus(customer_id, order_id),
            "active_handoff_id": active["handoff_id"] if active else None,
            "active_handoffs": [
                {"handoff_id": h["handoff_id"], "order_id": h.get("order_id"), "status": h["status"]}
                for h in active_list
            ],
            "handoff_mode": ("waiting" if active["status"] == "waiting" else "active") if active else "none",
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

    def _extract_verified_orders(self, customer_id: str, text: str | None) -> list[str]:
        out: list[str] = []
        for raw in ORDER_ID.findall(text or ""):
            norm = normalize_order_id(raw)
            if norm and norm not in out and self.data.lookup_for_customer(norm, customer_id)[1] is not None:
                out.append(norm)
        return out

    def _route_to_active_handoff(self, active: dict, thread_id: str, customer_id: str, text: str, snapshot,
                                 *, bind_order_id: str | None = None) -> dict:
        messages = (snapshot.values or {}).get("messages", [])
        visible = visible_messages(messages)
        clean_text = text.strip()
        followups = active.get("followups") or []
        is_dup_waiting = (
            active.get("status") == "waiting"
            and not bind_order_id
            and (
                (not followups and active.get("request_text") == clean_text)
                or (followups and followups[-1].get("sender_role") == "customer" and followups[-1].get("text") == clean_text)
            )
        )
        if is_dup_waiting:
            updated = active
        else:
            updated = self.store.append_handoff_followup(
                active["handoff_id"], sender_role="customer", sender_id=customer_id,
                text=clean_text, customer_id=customer_id, after_index=len(visible),
                order_id=bind_order_id if not active.get("order_id") else None,
            )
        self._record(
            event="customer_handoff_message", customer_id=customer_id, thread_id=thread_id,
            outcome="handoff_message_sent", order_id=updated["order_id"], handoff_id=active["handoff_id"],
        )
        return {
            "outcome": "handoff_message_sent", "reason_code": None, "messages": [],
            "confirmation": None, "ticket": None, "handoff": handoff_copy(updated, thread_id), "created": False,
        }

    def _handle_active_handoff_turn(self, active: dict, thread_id: str, customer_id: str, text: str, snapshot,
                                    focus_order_id: str | None = None) -> dict:
        """Route within the same order's handoff, or automatically split a new order into its own independent Hxxxx ID."""
        explicit_orders = self._extract_verified_orders(customer_id, text)
        explicit_focus = normalize_order_id(focus_order_id) if focus_order_id else None
        if explicit_focus and self.data.lookup_for_customer(explicit_focus, customer_id)[1] is None:
            explicit_focus = None
        target_orders = explicit_orders if explicit_orders else ([explicit_focus] if explicit_focus else [])
        wants_h = self._wants_human_or_second_appeal(text)

        if not target_orders:
            if active["status"] == "waiting" and wants_h:
                res = self._open_handoff(thread_id, customer_id, text, snapshot)
                return {"outcome": "handoff_requested" if res["created"] else "handoff_waiting",
                        "reason_code": None, "messages": [], "confirmation": None, "ticket": None, **res}
            return self._route_to_active_handoff(active, thread_id, customer_id, text, snapshot)

        if len(target_orders) == 1 and active.get("order_id") is None:
            oid = target_orders[0]
            if active["status"] == "waiting" and wants_h:
                res = self._open_handoff(thread_id, customer_id, text, snapshot, focus_order_id=oid, single_order=True)
                return {"outcome": "handoff_requested" if res["created"] else "handoff_waiting",
                        "reason_code": None, "messages": [], "confirmation": None, "ticket": None, **res}
            return self._route_to_active_handoff(active, thread_id, customer_id, text, snapshot, bind_order_id=oid)

        if target_orders == [active.get("order_id")]:
            if active["status"] == "waiting" and wants_h:
                res = self._open_handoff(thread_id, customer_id, text, snapshot, focus_order_id=target_orders[0], single_order=True)
                return {"outcome": "handoff_requested" if res["created"] else "handoff_waiting",
                        "reason_code": None, "messages": [], "confirmation": None, "ticket": None, **res}
            return self._route_to_active_handoff(active, thread_id, customer_id, text, snapshot)

        last_out: dict | None = None
        for oid in target_orders:
            existing_h = self.store.active_handoff_for_order(customer_id, oid, thread_id)
            if existing_h is None:
                unbound_h = self.store.unbound_active_handoff(customer_id, thread_id)
                if unbound_h is not None:
                    existing_h = unbound_h
            if existing_h is not None:
                if existing_h["status"] == "waiting" and wants_h:
                    res = self._open_handoff(thread_id, customer_id, text, snapshot, focus_order_id=oid, single_order=True)
                    last_out = {"outcome": "handoff_requested" if res["created"] else "handoff_waiting",
                                "reason_code": None, "messages": [], "confirmation": None, "ticket": None, **res}
                else:
                    bind_oid = oid if not existing_h.get("order_id") else None
                    last_out = self._route_to_active_handoff(existing_h, thread_id, customer_id, text, snapshot, bind_order_id=bind_oid)
            else:
                res = self._open_handoff(thread_id, customer_id, text, snapshot, focus_order_id=oid, single_order=True)
                last_out = {"outcome": "handoff_requested" if res["created"] else "handoff_waiting",
                            "reason_code": None, "messages": [], "confirmation": None, "ticket": None, **res}
        return last_out

    @staticmethod
    def _wants_human_or_second_appeal(text: str) -> bool:
        if wants_person(text):
            return True
        return bool(SECOND_APPEAL_RE.search(text) and not EXPLICIT_NO_HANDOFF_RE.search(text))

    async def stream_message(self, thread_id: str, customer_id: str, text: str, focus_order_id: str | None = None):
        """True async LangGraph astream with per-thread async lock, punctuation clause buffering & reply_risk guard."""
        async with self._async_lock(thread_id):
            snapshot = self.customer_graph.get_state(self._thread(thread_id))
            pending_confirm = first_request(snapshot.interrupts, "confirm_submission")
            active = self.store.active_handoff(customer_id, thread_id)
            if active and EXPLICIT_NO_HANDOFF_RE.search(text):
                for h in self.store.active_handoffs(customer_id, thread_id):
                    self.store.end_handoff(h["handoff_id"], customer_id=customer_id)
                active = None
            if active:
                if pending_confirm:
                    await self.customer_graph.ainvoke(Command(resume="cancel"), self._thread(thread_id), context=CustomerContext(customer_id))
                    snapshot = self.customer_graph.get_state(self._thread(thread_id))
                yield {"type": "done", "result": self._handle_active_handoff_turn(active, thread_id, customer_id, text, snapshot, focus_order_id=focus_order_id)}
                return
            if self._wants_human_or_second_appeal(text):
                if pending_confirm:
                    await self.customer_graph.ainvoke(Command(resume="cancel"), self._thread(thread_id), context=CustomerContext(customer_id))
                    snapshot = self.customer_graph.get_state(self._thread(thread_id))
                res = self._open_handoff(thread_id, customer_id, text, snapshot, focus_order_id=focus_order_id)
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
            cust_tickets = self.store.tickets(customer_id=customer_id)
            existing_statuses = {t["status"] for t in cust_tickets} | {"pending"}
            allowed = {float(self.policy.coupon_yuan)} | {
                float(t[k])
                for t in cust_tickets
                for k in ("proposed_coupon_yuan", "coupon_issued_yuan")
                if t.get(k) is not None
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
                        stream_nodes = ("agent",) if self.agent_mode == "B" else ("agent", "assess")
                        if node_name in stream_nodes and getattr(msg_chunk, "content", None) and not getattr(msg_chunk, "tool_calls", None):
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
            ret_model, llm_calls = extract_returned_model(new_messages)
            if ret_model:
                self.last_returned_model = ret_model
            usage = token_usage(new_messages)
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
            self._record(
                event="customer_message_stream", customer_id=customer_id, thread_id=thread_id,
                outcome=result.get("outcome"), reason_code=result.get("reason_code"),
                order_id=order_id, ticket_id=ticket["ticket_id"] if ticket else None,
                latency_ms=latency_ms, llm_calls=llm_calls, returned_model_id=ret_model, usage=usage,
                raw_proposal=result.get("raw_proposal"),
                unsafe_proposal=result.get("unsafe_proposal"),
                safety_intercept=result.get("safety_intercept"),
            )
            yield {
                "type": "done",
                "result": {
                    "outcome": result.get("outcome"),
                    "reason_code": result.get("reason_code"),
                    "messages": vis,
                    "confirmation": confirmation,
                    "ticket": customer_copy(ticket) if ticket else None,
                    "raw_proposal": result.get("raw_proposal"),
                    "unsafe_proposal": result.get("unsafe_proposal"),
                    "safety_intercept": result.get("safety_intercept"),
                    "latency_ms": latency_ms,
                    "llm_calls": llm_calls,
                    "returned_model_id": ret_model,
                    "usage": usage,
                },
            }

    def send_message(self, thread_id: str, customer_id: str, text: str, focus_order_id: str | None = None) -> dict:
        with self._lock(thread_id):
            snapshot = self.customer_graph.get_state(self._thread(thread_id))
            pending_confirm = first_request(snapshot.interrupts, "confirm_submission")
            active = self.store.active_handoff(customer_id, thread_id)
            if active and EXPLICIT_NO_HANDOFF_RE.search(text):
                for h in self.store.active_handoffs(customer_id, thread_id):
                    self.store.end_handoff(h["handoff_id"], customer_id=customer_id)
                active = None
            if active:
                if pending_confirm:
                    self._run(thread_id, customer_id, Command(resume="cancel"), "customer_cancel", snapshot)
                    snapshot = self.customer_graph.get_state(self._thread(thread_id))
                return self._handle_active_handoff_turn(
                    active, thread_id, customer_id, text, snapshot, focus_order_id=focus_order_id
                )
            # Emergency human-handoff, second-appeal & P0 food-safety escape hatches ALWAYS work, even if a confirmation card was open!
            if self._wants_human_or_second_appeal(text):
                if pending_confirm:
                    self._run(thread_id, customer_id, Command(resume="cancel"), "customer_cancel", snapshot)
                    snapshot = self.customer_graph.get_state(self._thread(thread_id))
                result = self._open_handoff(thread_id, customer_id, text, snapshot, focus_order_id=focus_order_id)
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
        ret_model, llm_calls = extract_returned_model(new_messages)
        if ret_model:
            self.last_returned_model = ret_model
        usage = token_usage(new_messages)
        ticket = self.store.get(result["ticket_id"]) if result.get("ticket_id") else None
        if result.get("outcome") == "ticket_created":
            self._open_review(ticket["ticket_id"])
        confirmation = first_request(result.get("__interrupt__"), "confirm_submission")
        order_id = requested_order(new_messages) or (confirmation or waiting or ticket or {}).get("order_id")
        guarded = {"guarded": result.get("guarded")} if result.get("reason_code") == "reply_guarded" else {}
        self._record(
            event=event, customer_id=customer_id, thread_id=thread_id, outcome=result.get("outcome"),
            reason_code=result.get("reason_code"), order_id=order_id,
            ticket_id=ticket["ticket_id"] if ticket else None,
            latency_ms=latency_ms, llm_calls=llm_calls, returned_model_id=ret_model, usage=usage,
            raw_proposal=result.get("raw_proposal"),
            unsafe_proposal=result.get("unsafe_proposal"),
            safety_intercept=result.get("safety_intercept"),
            **guarded,
        )
        return {
            "outcome": result.get("outcome"),
            "reason_code": result.get("reason_code"),
            "messages": visible_messages(new_messages),
            "confirmation": confirmation,
            "ticket": customer_copy(ticket) if ticket else None,
            "raw_proposal": result.get("raw_proposal"),
            "unsafe_proposal": result.get("unsafe_proposal"),
            "safety_intercept": result.get("safety_intercept"),
            "latency_ms": latency_ms,
            "llm_calls": llm_calls,
            "returned_model_id": ret_model,
            "usage": usage,
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
                        files: list[dict] | None = None, focus_order_id: str | None = None) -> dict:
        snapshot = self.customer_graph.get_state(self._thread(thread_id))
        return self._open_handoff(thread_id, customer_id, text, snapshot, files or [], focus_order_id=focus_order_id)

    def _resolve_handoff_order(self, customer_id: str, text: str | None, confirmation: dict | None,
                               messages, focus_order_id: str | None = None,
                               thread_id: str | None = None) -> str | None:
        explicit = self._extract_verified_orders(customer_id, text)
        if explicit:
            return explicit[-1]
        if focus_order_id:
            norm_focus = normalize_order_id(focus_order_id)
            if norm_focus and self.data.lookup_for_customer(norm_focus, customer_id)[1] is not None:
                return norm_focus
        cur_active = self.store.active_handoff(customer_id, thread_id) if thread_id else None
        candidates = [
            (confirmation or {}).get("order_id"),
            cur_active.get("order_id") if cur_active else None,
            last_verified_order(messages, customer_id, self.data),
        ]
        for cand in candidates:
            if cand and self.data.lookup_for_customer(cand, customer_id)[1] is not None:
                return cand
        # Fallback to latest ticket of this customer if no order appeared in chat yet
        cust_tickets = self.store.tickets(customer_id=customer_id)
        return cust_tickets[-1]["order_id"] if cust_tickets else None

    def _open_handoff(self, thread_id: str, customer_id: str, text: str | None, snapshot,
                      files: list[dict] | None = None, focus_order_id: str | None = None,
                      *, single_order: bool = False) -> dict:
        if not single_order:
            explicit_orders = self._extract_verified_orders(customer_id, text)
            if len(explicit_orders) > 1:
                last_res: dict | None = None
                for idx, oid in enumerate(explicit_orders):
                    batch_files = (files or []) if idx == len(explicit_orders) - 1 else []
                    last_res = self._open_handoff(
                        thread_id, customer_id, text, snapshot, batch_files,
                        focus_order_id=oid, single_order=True,
                    )
                return last_res

        messages = (snapshot.values or {}).get("messages", [])
        visible = visible_messages(messages)
        confirmation = first_request(snapshot.interrupts, "confirm_submission")
        if single_order and focus_order_id:
            order_id = normalize_order_id(focus_order_id)
        else:
            order_id = self._resolve_handoff_order(customer_id, text, confirmation, messages, focus_order_id, thread_id=thread_id)
        initial_appeal = extract_initial_appeal(visible, order_id, text)
        excerpt = build_handoff_excerpt(visible, order_id)
        order_obj = self.data.orders.get(order_id or "") or {}
        tenant_id = str(order_obj.get("tenant_id") or "M_67REST")

        # One-Order-One-Handoff ("一单一编号"): only continue a replied session if it belongs to THIS SAME order!
        if order_id:
            active = self.store.active_handoff_for_order(customer_id, order_id, thread_id)
            if active is None:
                active = self.store.unbound_active_handoff(customer_id, thread_id)
        else:
            active = self.store.active_handoff(customer_id, thread_id)

        if active and active["status"] == "replied":
            clean_text = text.strip() if text and text.strip() else None
            if not clean_text and files:
                clean_text = "🎤 已发送语音留言" if any(f.get("kind") == "audio" for f in files) else "📷 已上传补充凭证"
            try:
                updated = self.store.append_handoff_followup(
                    active["handoff_id"], sender_role="customer", sender_id=customer_id,
                    text=clean_text,
                    customer_id=customer_id, after_index=len(visible),
                    order_id=order_id if not active.get("order_id") else None, files=files or [],
                )
            except ValueError as exc:
                if "attachment_quota_exceeded" in str(exc):
                    raise ServiceError(409, "attachment_limit", "单次人工咨询最多上传 3 个附件。") from None
                if "customer_disk_quota_exceeded" in str(exc):
                    raise ServiceError(413, "customer_quota_exceeded", "当前账号累计上传凭证容量已达上限（25 MB）。") from None
                raise
            self._record(event="handoff_continue", customer_id=customer_id, thread_id=thread_id,
                         outcome="continued", order_id=updated["order_id"], handoff_id=active["handoff_id"])
            return {"handoff": handoff_copy(updated, thread_id), "created": False}

        try:
            handoff, created = self.store.create_handoff(
                customer_id=customer_id, thread_id=thread_id, order_id=order_id, after_index=len(visible),
                request_text=text, excerpt=excerpt, files=files or [], limit=HANDOFF_LIMIT,
                tenant_id=tenant_id, initial_appeal=initial_appeal)
        except ValueError as exc:
            if "attachment_quota_exceeded" in str(exc):
                raise ServiceError(409, "attachment_limit", "单次人工咨询最多上传 3 个附件。") from None
            if "customer_disk_quota_exceeded" in str(exc):
                raise ServiceError(413, "customer_quota_exceeded", "当前账号累计上传凭证容量已达上限（25 MB）。") from None
            raise
        if handoff is None:
            raise ServiceError(429, "handoff_limit", "当前人工排队人数已满，请稍后再试。")
        wait_followup = text.strip() if (text and text.strip() and not BARE_HANDOFF.fullmatch(text)) else None
        if not wait_followup and not created and files:
            wait_followup = "🎤 已发送语音留言" if any(f.get("kind") == "audio" for f in files) else "📷 已上传补充凭证"
        if not created and wait_followup:
            prior_f = handoff.get("followups") or []
            is_dup = (
                (not prior_f and handoff.get("request_text") == wait_followup)
                or (prior_f and prior_f[-1].get("sender_role") == "customer" and prior_f[-1].get("text") == wait_followup)
            )
            if not is_dup or files:
                handoff = self.store.append_handoff_followup(
                    handoff["handoff_id"], sender_role="customer", sender_id=customer_id,
                    text=wait_followup, customer_id=customer_id, after_index=len(visible),
                    order_id=order_id if not handoff.get("order_id") else None,
                ) or handoff
        self._record(event="handoff_request", customer_id=customer_id, thread_id=thread_id,
                     outcome="waiting" if created else "already_waiting", order_id=handoff["order_id"],
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

    def end_handoff(self, thread_id: str, customer_id: str, handoff_id: str) -> dict:
        """End an active human service session so future chat messages return to AI mode."""
        handoff = self.store.end_handoff(handoff_id, customer_id=customer_id)
        if handoff is None:
            raise ServiceError(404, "handoff_not_found", "当前账号下没有这条人工咨询。")
        self._record(event="handoff_end", customer_id=customer_id, outcome="ended",
                     order_id=handoff["order_id"], handoff_id=handoff_id)
        return {"handoff": handoff_copy(handoff, thread_id)}

    def customer_handoff_followup(self, thread_id: str, customer_id: str, handoff_id: str, text: str) -> dict:
        """Allow customer to send a two-way reply back to the human specialist on an active/replied handoff."""
        if not isinstance(text, str) or not text.strip():
            raise ServiceError(400, "invalid_text", "请填写追加留言内容。")
        text = text.strip()
        if len(text) > REPLY_LIMIT:
            raise ServiceError(400, "text_too_long", f"留言不能超过 {REPLY_LIMIT} 个字。")
        cur_after = self._visible_len(thread_id)
        updated = self.store.append_handoff_followup(
            handoff_id, sender_role="customer", sender_id=customer_id, text=text,
            customer_id=customer_id, after_index=cur_after,
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
        self._assert_action_permission(reviewer_id, "ticket_approve")
        tenant_id = self._reviewer_tenant(reviewer_id)
        approved_ids: list[str] = []
        skipped_ids: list[str] = []
        for raw_ticket in self.store.tickets(tenant_id=tenant_id):
            if raw_ticket["status"] != "pending":
                continue
            enriched = self._enrich_review_ticket(raw_ticket)
            if enriched.get("stp_tier") == "STP_L1_GREEN" or enriched.get("merchant_bear_yuan") == 0:
                order = self.data.orders.get(raw_ticket["order_id"])
                try:
                    self._validate_issue_amount_and_role(reviewer_id, order, None, None, check_paid_cap=True)
                except ServiceError:
                    skipped_ids.append(raw_ticket["ticket_id"])
                    continue
                note = "平台准时保池 100% 直赔（本店按时出餐 ¥0 承担）"
                self.decide(raw_ticket["ticket_id"], reviewer_id, "approve", note)
                approved_ids.append(raw_ticket["ticket_id"])
        return {"approved_ticket_ids": approved_ids, "skipped_ticket_ids": skipped_ids, "count": len(approved_ids)}

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

    def _review_handoff_item(self, item: dict) -> dict:
        oid = item.get("order_id") or ""
        rel_ticket = self.store.find(oid, self.policy.version) if oid else None
        copied = review_handoff_copy(item, self.data.orders.get(oid), rel_ticket)
        copied["attachments"] = [{**attachment, "url": f"/api/media/{attachment['attachment_id']}"}
                                 for attachment in copied.get("attachments", [])]
        copied["action_logs"] = self.store.action_logs(
            handoff_id=item["handoff_id"],
            ticket_id=rel_ticket["ticket_id"] if rel_ticket else None,
            include_internal=True,
        )
        return copied

    def review_handoffs(self, reviewer_id: str | None = None) -> dict:
        tenant_id = self._reviewer_tenant(reviewer_id)
        items = [self._review_handoff_item(item) for item in self.store.handoffs(tenant_id=tenant_id)]
        waiting = sorted(
            items,
            key=lambda x: (0 if x.get("priority") == "P0_FOOD_SAFETY" else 1, 0 if x.get("is_expedited") else 1, x["handoff_id"]),
        )
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
        rev = self._assert_action_permission(reviewer_id, "handoff_reply")
        existing_h = self.store.get_handoff(handoff_id)
        if existing_h is None:
            raise ServiceError(404, "handoff_not_found", "没有这条人工咨询。")
        self._assert_tenant_access(reviewer_id, existing_h.get("tenant_id"))
        started = time.perf_counter()
        cur_after = self._visible_len(existing_h.get("thread_id") or "")
        handoff = self.store.close_handoff(
            handoff_id, status="replied", reviewer_id=reviewer_id, reply_text=text, reply_after_index=cur_after
        )
        if handoff is None:
            raise ServiceError(409, "handoff_closed", "顾客已取消，或这条咨询已经回复。")
        self.store.log_action(
            handoff_id=handoff_id, order_id=handoff.get("order_id"), ticket_id=None,
            actor_id=reviewer_id, actor_name=rev.get("display_name"), actor_role=rev.get("role"),
            action="handoff_reply", action_label="首次回复顾客",
            before_status="waiting", after_status="replied", note=text[:120],
        )
        self._record(event="handoff_reply", reviewer_id=reviewer_id, customer_id=handoff["customer_id"],
                     outcome="replied", order_id=handoff["order_id"], handoff_id=handoff_id,
                     latency_ms=round((time.perf_counter() - started) * 1000))
        return {"handoff": self._review_handoff_item(handoff)}

    def followup_handoff(self, handoff_id: str, reviewer_id: str, text) -> dict:
        """Send an additional follow-up message on an already-replied handoff (eliminates 1-message lockout)."""
        if not isinstance(text, str) or not text.strip():
            raise ServiceError(400, "invalid_text", "请填写追回内容。")
        text = text.strip()
        if len(text) > REPLY_LIMIT:
            raise ServiceError(400, "text_too_long", f"回复不能超过 {REPLY_LIMIT} 个字。")
        rev = self._assert_action_permission(reviewer_id, "handoff_reply")
        existing_h = self.store.get_handoff(handoff_id)
        if existing_h is None:
            raise ServiceError(404, "handoff_not_found", "没有这条人工咨询或顾客已取消。")
        self._assert_tenant_access(reviewer_id, existing_h.get("tenant_id"))
        cur_after = self._visible_len(existing_h.get("thread_id") or "")
        updated = self.store.append_handoff_followup(
            handoff_id, sender_role="reviewer", sender_id=reviewer_id, text=text, after_index=cur_after
        )
        if updated is None:
            raise ServiceError(404, "handoff_not_found", "没有这条人工咨询或顾客已取消。")
        self.store.log_action(
            handoff_id=handoff_id, order_id=updated.get("order_id"), ticket_id=None,
            actor_id=reviewer_id, actor_name=rev.get("display_name"), actor_role=rev.get("role"),
            action="handoff_followup", action_label="追加跟进回复",
            before_status=existing_h.get("status"), after_status=updated.get("status"), note=text[:120],
        )
        self._record(event="handoff_followup", reviewer_id=reviewer_id, customer_id=updated["customer_id"],
                     outcome="followup_sent", order_id=updated["order_id"], handoff_id=handoff_id)
        return {"handoff": self._review_handoff_item(updated)}

    def _append_system_handoff_msg(self, handoff: dict, reviewer_id: str, text: str) -> None:
        cur_after = self._visible_len(handoff.get("thread_id") or "")
        self.store.append_handoff_followup(
            handoff["handoff_id"], sender_role="system", sender_id=reviewer_id, text=text, after_index=cur_after
        )

    @staticmethod
    def _require_note(raw_note, err_msg: str, limit: int = 200) -> str:
        if not isinstance(raw_note, str) or not raw_note.strip():
            raise ServiceError(400, "note_required", err_msg)
        cleaned = raw_note.strip()
        if len(cleaned) > limit:
            raise ServiceError(400, "note_too_long", f"说明内容不能超过 {limit} 个字。")
        return cleaned

    @staticmethod
    def _optional_note(raw_note, default: str, limit: int = 200) -> str:
        if not isinstance(raw_note, str) or not raw_note.strip():
            return default
        cleaned = raw_note.strip()
        if len(cleaned) > limit:
            raise ServiceError(400, "note_too_long", f"说明内容不能超过 {limit} 个字。")
        return cleaned

    def _validate_issue_amount_and_role(
        self,
        reviewer_id: str,
        order: dict | None,
        raw_amount,
        raw_note,
        *,
        check_paid_cap: bool = True,
    ) -> tuple[int, str | None]:
        """Enforce human-review-v1 HR04 (role), HR05 (1..20 integer + custom reason), HR06 (<= trusted paid amount)."""
        default_amt = int(self.policy.coupon_yuan)
        rev = self.data.reviewers.get(reviewer_id) or {}
        is_supervisor = (reviewer_id == "R002") or (rev.get("role") == "supervisor") or (
            "ticket_custom_amount" in (rev.get("permissions") or [])
        )

        if raw_amount is None or raw_amount == "":
            amt = default_amt
            explicit_custom = False
        else:
            if isinstance(raw_amount, bool):
                raise ServiceError(400, "invalid_amount", "补偿金额须为 1 至 20 元之间的整数。")
            if isinstance(raw_amount, int):
                amt = raw_amount
            elif isinstance(raw_amount, float):
                if not raw_amount.is_integer():
                    raise ServiceError(
                        400,
                        "non_integer_amount",
                        "补偿金额须为 1 至 20 元之间的整数，不支持小数金额（不自动四舍五入）。",
                    )
                amt = int(raw_amount)
            elif isinstance(raw_amount, str):
                s = raw_amount.strip()
                if not re.fullmatch(r"[+-]?\d+", s):
                    raise ServiceError(
                        400,
                        "non_integer_amount",
                        "补偿金额须为 1 至 20 元之间的整数，不支持小数或非数字输入。",
                    )
                amt = int(s)
            else:
                raise ServiceError(400, "invalid_amount", "补偿金额须为 1 至 20 元之间的整数。")
            explicit_custom = (amt != default_amt)

        if explicit_custom and not is_supervisor:
            raise ServiceError(
                403,
                "custom_amount_supervisor_only",
                f"普通客服仅可按标准 ¥{default_amt} 处理；自定义补偿金额须由主管专席（R002）审批。",
            )

        if amt < 1 or amt > 20:
            raise ServiceError(
                400,
                "amount_out_of_range",
                "补偿金额须为 1 至 20 元之间的整数，系统不会自动截断为边界值。",
            )

        cleaned_note: str | None = None
        if isinstance(raw_note, str) and raw_note.strip():
            cleaned_note = raw_note.strip()
            if len(cleaned_note) > 200:
                raise ServiceError(400, "note_too_long", "说明内容不能超过 200 个字。")
        if explicit_custom and not cleaned_note:
            raise ServiceError(
                400,
                "custom_amount_reason_required",
                f"主管调整非标准补偿金额（非 ¥{default_amt}）必须填写具体调整原因。",
            )

        if check_paid_cap:
            if not isinstance(order, dict):
                raise ServiceError(409, "unverified_paid_amount", "订单实付金额无法核实，暂不可发放补偿。")
            paid_raw = order.get("amount_yuan")
            if paid_raw is None or isinstance(paid_raw, bool) or not isinstance(paid_raw, (int, float)) or float(paid_raw) <= 0:
                raise ServiceError(
                    409,
                    "unverified_paid_amount",
                    "该订单缺少可信实付金额记录，系统不凭聊天自报金额发放补偿，请先核实订单实付。",
                )
            paid_val = float(paid_raw)
            if float(amt) > paid_val:
                if not explicit_custom:
                    raise ServiceError(
                        409,
                        "standard_amount_exceeds_paid",
                        f"标准补偿 ¥{amt} 超过订单可信实付金额 ¥{paid_raw:g}，系统不自动降额，请转交主管（R002）在实付上限内审批。",
                    )
                raise ServiceError(
                    409,
                    "amount_exceeds_paid",
                    f"补偿金额 ¥{amt} 不可超过订单可信实付金额 ¥{paid_raw:g}。",
                )

        return amt, cleaned_note

    def _validate_reconsideration(
        self,
        ticket: dict,
        raw_note,
        raw_reason_type=None,
    ) -> tuple[str, str]:
        """Enforce human-review-v1 HR01/HR02/HR03 reconsideration rules."""
        if self.store.compensated_for_order(ticket["order_id"]) is not None or ticket["status"] == "approved":
            raise ServiceError(
                409,
                "already_compensated_no_reconsider",
                "该订单已完成唯一补偿发放（一单一赔），不支持重审、改额或补差价。",
            )
        if ticket["status"] != "rejected":
            raise ServiceError(
                409,
                "invalid_ticket_state",
                "仅「已驳回且未发放补偿」的原申请单允许发起重审。",
            )
        cleaned_note = self._require_note(
            raw_note,
            "发起重审或改判已驳回申请必须写明原因（可核实的相关新信息或原处理错误）。",
        )
        rt = str(raw_reason_type).strip() if raw_reason_type is not None else ""
        if rt and rt not in VALID_RECONSIDER_REASONS:
            raise ServiceError(
                400,
                "invalid_reconsider_reason_type",
                "重审原因类型须为 verifiable_relevant_new_information（可核实的新信息）或 prior_processing_error（原处理错误）；仅因不满结论不得重审。",
            )
        return cleaned_note, (rt or "verifiable_relevant_new_information")

    def perform_handoff_action(self, handoff_id: str, reviewer_id: str, payload: dict) -> dict:
        """Execute a closed-loop ticket or order handling action inside a human agent session."""
        action = payload.get("action")
        if action in ("change_amount", "top_up"):
            self._assert_action_permission(reviewer_id, "ticket_approve")
            raise ServiceError(
                409,
                "post_issue_amount_change_disallowed",
                "已成功发放补偿的订单遵循一单一赔，不支持事后改额或补差价。",
            )
        perm_map = {
            "approve_compensation": ("ticket_approve", "同意补偿"),
            "approve": ("ticket_approve", "通过申请"),
            "uphold_reject": ("ticket_reject", "维持驳回"),
            "reject": ("ticket_reject", "驳回申请"),
            "request_info": ("ticket_request_info", "要求补充材料"),
            "escalate": ("ticket_escalate", "升级主管"),
            "expedite": ("ticket_expedite", "加急处理"),
            "transfer": ("ticket_transfer", "转交他席"),
            "reopen": ("ticket_reopen", "发起重审"),
            "urge_or_reassign": ("order_urge", "催单/改派"),
            "internal_note": ("order_note", "内部备注"),
            "create_ticket": ("order_ticket", "创建工单"),
            "close_session": ("handoff_close", "结束会话"),
        }
        if not isinstance(action, str) or action not in perm_map:
            raise ServiceError(400, "invalid_action", "不支持这个处理动作。")
        perm, action_label = perm_map[action]
        rev = self._assert_action_permission(reviewer_id, perm)
        actor_name = rev.get("display_name") or reviewer_id
        actor_role = rev.get("role") or "agent"

        with self._review_lock:
            handoff = self.store.get_handoff(handoff_id)
            if handoff is None:
                raise ServiceError(404, "handoff_not_found", "没有这条人工咨询。")
            self._assert_tenant_access(reviewer_id, handoff.get("tenant_id"))
            if handoff["status"] == "cancelled":
                raise ServiceError(409, "handoff_cancelled", "顾客已取消这条人工咨询。")

            oid = handoff.get("order_id")
            order = self.data.orders.get(oid) if oid else None
            ticket = self.store.find(oid, self.policy.version) if oid else None
            tid = ticket["ticket_id"] if ticket else None

            sys_msg: str | None = None
            before_st: str | None = None
            after_st: str | None = None
            before_amt: float | None = ticket.get("coupon_issued_yuan") if ticket else None
            amt_val: float | None = None
            log_note: str | None = None
            reason_type: str | None = None
            issue_result: str | None = None
            deduplicated = False
            is_internal = False
            transition_replied = False
            close_session = False

            if action in ("approve_compensation", "approve"):
                if not order:
                    raise ServiceError(409, "ticket_required", "当前会话未关联具体订单，无法执行补偿审批。")
                if payload.get("intent") in ("change_amount", "top_up"):
                    raise ServiceError(
                        409,
                        "post_issue_amount_change_disallowed",
                        "已成功发放补偿的订单不支持事后改额或补差价。",
                    )
                amt_val, cleaned_note = self._validate_issue_amount_and_role(
                    reviewer_id, order, payload.get("amount_yuan"), payload.get("note"), check_paid_cap=True
                )
                existing_comp = self.store.compensated_for_order(oid) if oid else None
                if existing_comp is not None or (ticket and ticket["status"] == "approved" and ticket.get("coupon_issued_yuan") is not None):
                    comp_ticket = existing_comp or ticket
                    self.store.log_action(
                        handoff_id=handoff_id, order_id=oid, ticket_id=comp_ticket["ticket_id"],
                        actor_id=reviewer_id, actor_name=actor_name, actor_role=actor_role,
                        action=action, action_label="重复审批拦截",
                        before_status="approved", after_status="approved",
                        before_amount_yuan=comp_ticket.get("coupon_issued_yuan"),
                        amount_yuan=comp_ticket.get("coupon_issued_yuan"),
                        note=cleaned_note or "已有唯一补偿记录，返回原状态未重复发券",
                        issue_result="already_compensated_no_new_issue",
                    )
                    raise ServiceError(
                        409,
                        "ticket_already_approved",
                        f"该订单已完成唯一补偿发放（¥{comp_ticket.get('coupon_issued_yuan')}），返回已有结果且不重复发券。",
                        extra={
                            "deduplicated": True,
                            "issue_result": "already_compensated_no_new_issue",
                            "existing_status": comp_ticket["status"],
                            "ticket": self._enrich_review_ticket(comp_ticket),
                        },
                    )
                if ticket is not None and ticket["status"] == "rejected":
                    cleaned_note, reason_type = self._validate_reconsideration(
                        ticket, payload.get("note"), payload.get("reason_type")
                    )
                if ticket is None:
                    decision = evaluate_order(order_facts(order), self.policy)
                    sub_init = compute_actuarial_subrogation(order, self.policy)
                    ticket, _ = self.store.create_manual_ticket(
                        customer_id=handoff["customer_id"], order=order, policy_version=self.policy.version,
                        late_seconds=int(decision.get("late_seconds") or 0),
                        proposed_coupon_yuan=amt_val, reviewer_id=reviewer_id,
                        subrogation=sub_init, note="人工客服审批补偿时自动补建订单申请单",
                    )
                    tid = ticket["ticket_id"]
                log_note = cleaned_note or f"人工客服核实通过，发放 ¥{amt_val} 无门槛补偿券。"
                sub = compute_actuarial_subrogation(order, self.policy) if order else {}
                orig_prop = max(1.0, float(ticket.get("proposed_coupon_yuan") or amt_val))
                m_orig = float(sub.get("merchant_bear_yuan") or 0.0)
                ratio = min(1.0, m_orig / orig_prop) if orig_prop > 0 else 0.0
                m_bear = round(amt_val * ratio, 1)
                p_bear = round(max(0.0, amt_val - m_bear), 1)
                updated, before_st = self.store.decide_or_override_ticket(
                    tid, target_status="approved", reviewer_id=reviewer_id, note=log_note,
                    amount_yuan=amt_val, merchant_bear_yuan=m_bear, platform_bear_yuan=p_bear,
                    action_name="approved", reason_type=reason_type, issue_result="issued",
                )
                if updated and updated.pop("_deduplicated", False):
                    raise ServiceError(
                        409,
                        "ticket_already_approved",
                        f"该订单已完成唯一补偿发放（¥{updated.get('coupon_issued_yuan')}），返回已有结果且不重复发券。",
                        extra={
                            "deduplicated": True,
                            "issue_result": "already_compensated_no_new_issue",
                            "existing_status": updated["status"],
                            "ticket": self._enrich_review_ticket(updated),
                        },
                    )
                ticket = updated
                after_st = "approved"
                issue_result = "issued"
                sys_msg = (
                    f"系统通知：客服已通过补偿申请（订单 {oid} · 申请单 {tid} · 人工处理单 {handoff_id}），"
                    f"¥{amt_val} 无门槛补偿券已发放至您的账户（即时到账）。说明：{log_note}"
                )
                transition_replied = True

            elif action in ("uphold_reject", "reject"):
                if oid and self.store.compensated_for_order(oid) is not None:
                    raise ServiceError(409, "already_compensated_immutable", "该订单已完成补偿发放，不可改为驳回。")
                log_note = self._require_note(payload.get("note"), "驳回或维持驳回必须填写具体理由（顾客可见）。")
                if ticket is None:
                    if action == "reject" and order:
                        decision = evaluate_order(order_facts(order), self.policy)
                        sub_init = compute_actuarial_subrogation(order, self.policy)
                        ticket, _ = self.store.create_manual_ticket(
                            customer_id=handoff["customer_id"], order=order, policy_version=self.policy.version,
                            late_seconds=int(decision.get("late_seconds") or 0),
                            proposed_coupon_yuan=int(decision.get("proposed_coupon_yuan") or self.policy.coupon_yuan),
                            reviewer_id=reviewer_id, subrogation=sub_init, note="人工客服驳回时自动补建订单申请单",
                        )
                        tid = ticket["ticket_id"]
                    else:
                        raise ServiceError(409, "ticket_required", "当前订单尚无关联申请单。")
                if action == "reject" and ticket["status"] not in ("pending", "needs_info"):
                    raise ServiceError(409, "invalid_ticket_state", "当前申请单状态不支持直接驳回。")
                if action == "uphold_reject" and ticket["status"] != "rejected":
                    raise ServiceError(409, "invalid_ticket_state", "仅「已驳回」状态的申请单可执行维持驳回。")
                updated, before_st = self.store.decide_or_override_ticket(
                    tid, target_status="rejected", reviewer_id=reviewer_id, note=log_note,
                    action_name="uphold_rejected" if action == "uphold_reject" else "rejected",
                    issue_result="no_issue",
                )
                ticket = updated
                after_st = "rejected"
                issue_result = "no_issue"
                verb = "维持驳回" if action == "uphold_reject" else "驳回"
                sys_msg = f"系统通知：客服已{verb}申请（订单 {oid} · 申请单 {tid} · 人工处理单 {handoff_id}），理由：{log_note}"
                transition_replied = True

            elif action == "request_info":
                if ticket is None:
                    raise ServiceError(409, "ticket_required", "当前订单尚无关联申请单。")
                if self.store.compensated_for_order(ticket["order_id"]) is not None or ticket["status"] == "approved":
                    raise ServiceError(409, "already_compensated_immutable", "该订单已完成补偿发放，不支持要求补充材料。")
                if ticket["status"] not in ("rejected", "pending"):
                    raise ServiceError(409, "invalid_ticket_state", "当前申请单状态不支持要求补充材料。")
                if ticket["status"] == "rejected":
                    log_note, reason_type = self._validate_reconsideration(
                        ticket, payload.get("note"), payload.get("reason_type")
                    )
                else:
                    log_note = self._require_note(payload.get("note"), "请填写需要顾客补充的材料或说明。")
                updated, before_st = self.store.decide_or_override_ticket(
                    tid, target_status="needs_info", reviewer_id=reviewer_id, note=log_note,
                    action_name="information_requested", reason_type=reason_type, issue_result="no_issue",
                )
                ticket = updated
                after_st = "needs_info"
                issue_result = "no_issue"
                sys_msg = f"系统通知：客服已发起补充材料要求（{tid}）：{log_note}。请在右侧申请单卡片填写并提交。"
                transition_replied = True

            elif action == "escalate":
                log_note = self._optional_note(payload.get("note"), "已升级主管专席复核处理")
                before_st = ticket["status"] if ticket else handoff["status"]
                after_st = f"{before_st}(已升级主管)"
                self.store.update_handoff_flags(handoff_id, escalated_to="主管专席", is_expedited=1)
                if ticket:
                    ticket = self.store.update_ticket_flags(tid, escalated_to="主管专席", is_expedited=1)
                    self.store._event(tid, f"reviewer:{reviewer_id}", "escalated", log_note, now_text(),
                                      before_status=before_st, after_status=after_st)
                sys_msg = f"系统通知：本次咨询已升级主管专席加急复核（{log_note}）。"

            elif action == "expedite":
                log_note = self._optional_note(payload.get("note"), "已标记为加急优先处理")
                before_st = ticket["status"] if ticket else handoff["status"]
                after_st = f"{before_st}(加急)"
                self.store.update_handoff_flags(handoff_id, is_expedited=1)
                if ticket:
                    ticket = self.store.update_ticket_flags(tid, is_expedited=1)
                    self.store._event(tid, f"reviewer:{reviewer_id}", "expedited", log_note, now_text(),
                                      before_status=before_st, after_status=after_st)
                sys_msg = f"系统通知：客服已将该处理申请标记为加急优先（{log_note}）。"

            elif action == "transfer":
                target_id = payload.get("target_reviewer_id")
                if not target_id:
                    target_id = "R002" if reviewer_id != "R002" else "R001"
                target_rev = self.data.reviewers.get(target_id)
                if not target_rev or target_rev.get("can_handle") is False:
                    raise ServiceError(400, "invalid_transfer_target", "目标坐席不存在或无处理权限。")
                log_note = self._optional_note(payload.get("note"), f"转交至 {target_rev['display_name']}")
                before_st = handoff.get("assigned_reviewer_id") or handoff.get("reviewer_id") or reviewer_id
                after_st = target_id
                self.store.update_handoff_flags(handoff_id, assigned_reviewer_id=target_id)
                if ticket:
                    ticket = self.store.update_ticket_flags(tid, assigned_reviewer_id=target_id)
                    self.store._event(tid, f"reviewer:{reviewer_id}", "transferred",
                                      f"转交 {target_rev['display_name']}：{log_note}", now_text(),
                                      before_status=before_st, after_status=after_st)
                sys_msg = f"系统通知：会话已转交至 {target_rev['display_name']} 继续为您处理。"

            elif action == "reopen":
                if ticket is None:
                    raise ServiceError(409, "ticket_required", "当前订单尚无关联申请单。")
                log_note, reason_type = self._validate_reconsideration(
                    ticket, payload.get("note"), payload.get("reason_type")
                )
                updated, before_st = self.store.decide_or_override_ticket(
                    tid, target_status="pending", reviewer_id=reviewer_id, note=log_note,
                    action_name="reopened", reason_type=reason_type, issue_result="reconsidered_to_pending",
                )
                ticket = updated
                after_st = "pending"
                issue_result = "reconsidered_to_pending"
                self._open_review(tid)
                sys_msg = f"系统通知：客服已沿原申请单（{tid}）发起重审，状态恢复为待审核。重审原因：{log_note}"

            elif action == "urge_or_reassign":
                if not order:
                    raise ServiceError(400, "order_required", "当前会话未关联具体订单，无法执行催单/改派。")
                mode = payload.get("mode") or "urge"
                action_label = "改派运力" if mode == "reassign" else "催单提醒"
                log_note = self._optional_note(
                    payload.get("note"),
                    f"已向配送站点发起{action_label}（订单 {oid}）",
                )
                before_st = order.get("status") or "delivered"
                after_st = "已改派" if mode == "reassign" else "已催单"
                sys_msg = f"系统通知：客服已对订单 {oid} 发起「{action_label}」，{log_note}。"

            elif action == "internal_note":
                log_note = self._require_note(payload.get("note"), "请填写内部备注内容。", limit=300)
                before_st = ticket["status"] if ticket else handoff["status"]
                after_st = before_st
                is_internal = True

            elif action == "create_ticket":
                if not order:
                    raise ServiceError(400, "order_required", "当前会话未关联具体订单，无法创建工单。")
                if ticket is not None:
                    raise ServiceError(409, "ticket_already_exists", f"该订单已存在申请单 {tid}，请直接沿原单处理。")
                raw_prop = payload.get("amount_yuan")
                amt_val, cleaned_note = self._validate_issue_amount_and_role(
                    reviewer_id, order, raw_prop, payload.get("note"),
                    check_paid_cap=(raw_prop is not None and raw_prop != ""),
                )
                decision = evaluate_order(order_facts(order), self.policy)
                sub = compute_actuarial_subrogation(order, self.policy)
                log_note = cleaned_note or "人工客服在会话内为顾客创建售后申请单"
                ticket, created = self.store.create_manual_ticket(
                    customer_id=handoff["customer_id"], order=order, policy_version=self.policy.version,
                    late_seconds=int(decision.get("late_seconds") or 0),
                    proposed_coupon_yuan=amt_val, reviewer_id=reviewer_id,
                    subrogation=sub, note=log_note,
                )
                tid = ticket["ticket_id"]
                if created:
                    self._open_review(tid)
                before_st = "无工单"
                after_st = ticket["status"]
                issue_result = "pending_review"
                sys_msg = f"系统通知：客服已为您创建售后申请单 {tid}（订单 {oid}，建议补偿 ¥{amt_val}），正在审核处理。"

            elif action == "close_session":
                if handoff.get("ended_at"):
                    raise ServiceError(409, "handoff_already_closed", "该人工会话已经结束。")
                log_note = self._optional_note(payload.get("note"), "问题已核实处理完毕，本次人工服务结束")
                before_st = handoff["status"]
                after_st = "ended"
                sys_msg = f"系统通知：人工客服已结束本次服务（{log_note}）。如需继续咨询可随时发消息。"
                transition_replied = True
                close_session = True

            if sys_msg:
                self._append_system_handoff_msg(handoff, reviewer_id, sys_msg)
            if transition_replied or close_session:
                self.store.transition_handoff_status(handoff_id, reviewer_id=reviewer_id, close_session=close_session)

            action_log = self.store.log_action(
                handoff_id=handoff_id, order_id=oid, ticket_id=tid,
                actor_id=reviewer_id, actor_name=actor_name, actor_role=actor_role,
                action=action, action_label=action_label,
                before_status=before_st, after_status=after_st,
                before_amount_yuan=before_amt, amount_yuan=amt_val, note=log_note,
                reason_type=reason_type, issue_result=issue_result, is_internal=is_internal,
            )
            self._record(
                event="handoff_action", reviewer_id=reviewer_id, customer_id=handoff["customer_id"],
                handoff_id=handoff_id, order_id=oid, ticket_id=tid,
                action=action, outcome=after_st, amount_yuan=amt_val,
                reason_type=reason_type, issue_result=issue_result,
                deduplicated=deduplicated, is_internal=is_internal,
            )
            refreshed = self.store.get_handoff(handoff_id)
            return {
                "handoff": self._review_handoff_item(refreshed),
                "ticket": self._enrich_review_ticket(ticket) if ticket else None,
                "action_log": action_log,
                "deduplicated": deduplicated,
                "issue_result": issue_result,
            }

    def review_detail(self, ticket_id: str, reviewer_id: str | None = None) -> dict:
        raw = self._ticket_or_404(ticket_id)
        self._assert_tenant_access(reviewer_id, raw.get("tenant_id"))
        ticket = self._enrich_review_ticket(raw)
        request = self._open_review(ticket_id) if ticket["status"] == "pending" else None
        return {
            "ticket": ticket,
            "events": self.store.events(ticket_id),
            "action_logs": self.store.action_logs(ticket_id=ticket_id, include_internal=True),
            "request": request,
        }

    def reopen_ticket(
        self,
        ticket_id: str,
        reviewer_id: str,
        note: str | None,
        reason_type: str | None = None,
    ) -> dict:
        """Reopen a rejected, uncompensated ticket along its original ticket_id with mandatory written reason."""
        rev = self._assert_action_permission(reviewer_id, "ticket_reopen")
        with self._review_lock:
            current = self._ticket_or_404(ticket_id)
            self._assert_tenant_access(reviewer_id, current.get("tenant_id"))
            cleaned_note, validated_rt = self._validate_reconsideration(current, note, reason_type)
            updated, before_st = self.store.decide_or_override_ticket(
                ticket_id,
                target_status="pending",
                reviewer_id=reviewer_id,
                note=cleaned_note,
                action_name="reopened",
                reason_type=validated_rt,
                issue_result="reconsidered_to_pending",
            )
            self._open_review(ticket_id)
        self.store.log_action(
            handoff_id=None, order_id=updated["order_id"], ticket_id=ticket_id,
            actor_id=reviewer_id, actor_name=rev.get("display_name"), actor_role=rev.get("role"),
            action="reopen", action_label="发起重审",
            before_status=before_st, after_status="pending",
            before_amount_yuan=current.get("coupon_issued_yuan"), amount_yuan=None,
            note=cleaned_note, reason_type=validated_rt, issue_result="reconsidered_to_pending",
        )
        self._record(
            event="review_reopen", reviewer_id=reviewer_id, customer_id=updated["customer_id"],
            outcome="pending", order_id=updated["order_id"], ticket_id=ticket_id,
            reason_type=validated_rt, issue_result="reconsidered_to_pending",
        )
        return {"ticket": self._enrich_review_ticket(updated), "events": self.store.events(ticket_id)}

    def decide(
        self,
        ticket_id: str,
        reviewer_id: str,
        decision: str,
        note: str | None,
        amount_yuan=None,
    ) -> dict:
        if not isinstance(decision, str) or decision not in DECISION_STATUS:
            raise ServiceError(400, "invalid_decision", "不支持这个处理操作。")
        perm_key = {"approve": "ticket_approve", "reject": "ticket_reject", "request_info": "ticket_request_info"}[decision]
        rev = self._assert_action_permission(reviewer_id, perm_key)
        if decision == "request_info":
            if not isinstance(note, str) or not note.strip():
                raise ServiceError(400, "information_question_required", "请填写需要顾客补充的内容。")
            note = note.strip()
            if len(note) > 200:
                raise ServiceError(400, "note_too_long", "问题不能超过 200 个字。")

        amt_val: int | None = None
        m_bear: float | None = None
        p_bear: float | None = None
        with self._review_lock:
            current = self._ticket_or_404(ticket_id)
            self._assert_tenant_access(reviewer_id, current.get("tenant_id"))
            order = self.data.orders.get(current["order_id"])

            if decision == "approve":
                amt_val, cleaned_note = self._validate_issue_amount_and_role(
                    reviewer_id, order, amount_yuan, note, check_paid_cap=True
                )
                existing_comp = self.store.compensated_for_order(current["order_id"])
                if existing_comp is not None:
                    self.store.log_action(
                        handoff_id=None, order_id=existing_comp["order_id"], ticket_id=existing_comp["ticket_id"],
                        actor_id=reviewer_id, actor_name=rev.get("display_name"), actor_role=rev.get("role"),
                        action="approve_deduplicated", action_label="重复审批拦截",
                        before_status="approved", after_status="approved",
                        before_amount_yuan=existing_comp.get("coupon_issued_yuan"),
                        amount_yuan=existing_comp.get("coupon_issued_yuan"),
                        note=cleaned_note or "已有唯一补偿记录，返回原状态未重复发券",
                        issue_result="already_compensated_no_new_issue",
                    )
                    raise ServiceError(
                        409,
                        "ticket_already_decided",
                        f"该订单已完成唯一补偿发放（¥{existing_comp.get('coupon_issued_yuan')}），返回已有状态且不重复发券。",
                        extra={
                            "deduplicated": True,
                            "issue_result": "already_compensated_no_new_issue",
                            "existing_status": existing_comp["status"],
                            "ticket": self._enrich_review_ticket(existing_comp),
                        },
                    )
                note = cleaned_note or f"人工审核通过，按标准发放 ¥{amt_val} 无门槛补偿券。"
                sub = compute_actuarial_subrogation(order, self.policy) if order else {}
                orig_prop = max(1.0, float(current.get("proposed_coupon_yuan") or amt_val))
                m_orig = float(sub.get("merchant_bear_yuan") or 0.0)
                ratio = min(1.0, m_orig / orig_prop) if orig_prop > 0 else 0.0
                m_bear = round(amt_val * ratio, 1)
                p_bear = round(max(0.0, amt_val - m_bear), 1)
            else:
                if self.store.compensated_for_order(current["order_id"]) is not None:
                    raise ServiceError(409, "already_compensated_immutable", "该订单已完成唯一补偿发放，不支持撤回或变更状态。")

            if current["status"] == "needs_info":
                raise ServiceError(409, "customer_information_pending", "正在等待顾客补充信息。")
            if current["status"] != "pending":
                raise ServiceError(
                    409,
                    "ticket_already_decided",
                    "这张工单已经处理过（已驳回工单需先填写原因发起重审后再审批）。",
                    extra={"existing_status": current["status"], "ticket": self._enrich_review_ticket(current)},
                )
            if decision == "reject":
                if isinstance(note, str) and note.strip():
                    note = note.strip()
                    if len(note) > 200:
                        raise ServiceError(400, "note_too_long", "驳回原因不能超过 200 个字。")
                else:
                    note = "经人工复核暂不符合本次补偿条件，如有疑问可转人工继续咨询此订单。"
            self._open_review(ticket_id)
            started = time.perf_counter()
            answer = {
                "decision": decision,
                "reviewer_id": reviewer_id,
                "note": note,
                "amount_yuan": amt_val,
                "merchant_bear_yuan": m_bear,
                "platform_bear_yuan": p_bear,
            }
            result = self.review_graph.invoke(Command(resume=answer), self._review_thread(ticket_id))
            latency_ms = round((time.perf_counter() - started) * 1000)
            ticket = result.get("ticket")
            if ticket is None or ticket["status"] == "pending":
                raise ServiceError(409, "ticket_already_decided", "这张工单已经处理过。")
            was_dedup = bool(ticket.pop("_deduplicated", False))
        if was_dedup:
            raise ServiceError(
                409,
                "ticket_already_decided",
                f"该订单已完成唯一补偿发放（¥{ticket.get('coupon_issued_yuan')}），返回已有状态且不重复发券。",
                extra={
                    "deduplicated": True,
                    "issue_result": "already_compensated_no_new_issue",
                    "existing_status": ticket["status"],
                    "ticket": self._enrich_review_ticket(ticket),
                },
            )
        label_map = {"approve": "审核通过", "reject": "审核驳回", "request_info": "要求补充材料"}
        issue_res = "issued" if decision == "approve" else "no_issue"
        self.store.log_action(
            handoff_id=None, order_id=ticket["order_id"], ticket_id=ticket_id,
            actor_id=reviewer_id, actor_name=rev.get("display_name"), actor_role=rev.get("role"),
            action=decision, action_label=label_map[decision],
            before_status="pending", after_status=ticket["status"],
            before_amount_yuan=current.get("coupon_issued_yuan"),
            amount_yuan=ticket.get("coupon_issued_yuan"), note=note,
            issue_result=issue_res,
        )
        self._record(
            event="review_decision", reviewer_id=reviewer_id, customer_id=ticket["customer_id"],
            outcome=ticket["status"], order_id=ticket["order_id"], ticket_id=ticket_id,
            amount_yuan=ticket.get("coupon_issued_yuan"), issue_result=issue_res,
            latency_ms=latency_ms,
        )
        return {
            "ticket": self._enrich_review_ticket(ticket),
            "events": self.store.events(ticket_id),
            "deduplicated": False,
            "issue_result": issue_res,
        }

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
