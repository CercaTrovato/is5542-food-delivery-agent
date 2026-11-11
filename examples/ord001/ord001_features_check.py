# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = [
#     "langgraph==1.2.19",
#     "langchain==1.4.9",
#     "langchain-openai==1.7.4",
#     "starlette==1.10.0",
#     "uvicorn==0.54.0",
#     "httpx==0.28.1",
# ]
# ///

"""Check the 2026-11-11 additions in isolated TestClients; never touches a running server.

The application panel follows the order being asked about, the human handoff, the satisfaction rating,
the guard on model replies, and the in-place upgrade of an existing SQLite file.
"""

import argparse
import json
import sqlite3
import tempfile
from contextlib import ExitStack, contextmanager
from datetime import datetime
from pathlib import Path

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from starlette.testclient import TestClient

import ord001_web_service
from ord001_langchain import ScriptedOrderModel
from ord001_web import create_app
from ord001_web_service import DemoService, wants_person
from ord001_web_store import SCHEMA
from ord001_web_texts import GUARDED_REPLY

FOCUS_KEYS = {"order_id", "verified", "status", "reason_code", "late_seconds", "proposed_coupon_yuan", "ticket_id"}


class FixedReply(BaseChatModel):
    """Answers every turn with one fixed text, standing in for a model that over-promises."""

    reply: str = ""

    @property
    def _llm_type(self) -> str:
        return "fixed-reply"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=self.reply))])


def service(path=":memory:", model=None):
    return DemoService(model=model or ScriptedOrderModel(), db_path=str(path))


@contextmanager
def clients(svc):
    app = create_app(svc)
    with ExitStack() as stack:
        users = {name: stack.enter_context(TestClient(app)) for name in ("customer", "other", "reviewer", "anonymous")}
        post(users["customer"], "/api/customer/login", {"customer_id": "U001"})
        post(users["other"], "/api/customer/login", {"customer_id": "U002"})
        post(users["reviewer"], "/api/review/login", {"reviewer_id": "R001"})
        yield users


def post(client, url, body, expected=200):
    response = client.post(url, json=body)
    assert response.status_code == expected, (url, response.status_code, response.text)
    return response.json()


def get(client, url, expected=200):
    response = client.get(url)
    assert response.status_code == expected, (url, response.status_code, response.text)
    return response.json()


def say(users, text, who="customer"):
    return post(users[who], "/api/customer/messages", {"text": text})


def focus(users, who="customer"):
    return get(users[who], "/api/customer/state")["focus"]


def runs(users):
    return [run for run in get(users["reviewer"], "/api/review/runs")["runs"] if run["event"] != "reset"]


def approved_ticket(users, order_id="ORD001"):
    assert say(users, order_id)["confirmation"] is not None
    ticket = post(users["customer"], "/api/customer/confirm", {"answer": "confirm"})["ticket"]
    post(users["reviewer"], f"/api/review/tickets/{ticket['ticket_id']}/decision", {"decision": "approve", "note": "已核实。"})
    return ticket["ticket_id"]


def focus_follows_order():
    svc = service()
    try:
        with clients(svc) as users:
            assert focus(users) is None
            tid = approved_ticket(users)
            seen = {"ORD001": focus(users)}
            assert seen["ORD001"]["ticket_id"] == tid and set(seen["ORD001"]) == FOCUS_KEYS
            say(users, "我的外卖 ord002 迟到了，可以申请补偿吗？")
            reply = get(users["customer"], "/api/customer/state")["messages"][-1]["text"]
            assert "预计 18:00，实际 18:10，晚到 10 分钟" in reply, reply
            seen["ORD002"] = focus(users)
            assert seen["ORD002"] == {"order_id": "ORD002", "verified": True, "status": "ineligible",
                                      "reason_code": "delay_below_threshold", "late_seconds": 600,
                                      "proposed_coupon_yuan": None, "ticket_id": None}, seen["ORD002"]
            assert say(users, "ORD005")["confirmation"]["order_id"] == "ORD005"
            seen["ORD005"] = focus(users)
            assert seen["ORD005"]["status"] == "pending" and seen["ORD005"]["ticket_id"] is None
            assert seen["ORD005"]["late_seconds"] == 1801 and seen["ORD005"]["proposed_coupon_yuan"] == 10
            post(users["customer"], "/api/customer/confirm", {"answer": "cancel"})
            say(users, "你好")
            assert focus(users)["order_id"] == "ORD005", "A message without an order kept the last order"
            for order_id in ("ORD101", "ORD999"):
                say(users, order_id)
                seen[order_id] = focus(users)
                assert seen[order_id] == {"order_id": order_id, "verified": False}, seen[order_id]
            say(users, "ORD006")
            seen["ORD006"] = focus(users)
            assert seen["ORD006"]["reason_code"] == "not_delivered" and seen["ORD006"]["late_seconds"] is None
            # The owner of ORD101 asking about U001's ORD001 learns nothing about it or its ticket.
            say(users, "ORD001", who="other")
            seen["U002 asks ORD001"] = focus(users, "other")
            assert seen["U002 asks ORD001"] == {"order_id": "ORD001", "verified": False}
            assert get(users["other"], "/api/customer/state")["tickets"] == []
            assert all(run["event"] != "focus" for run in runs(users)), "Reading the panel must not write the run log"
            return {"focus": seen, "ticket_id": tid}
    finally:
        svc.store.close()


def handoff_words():
    cases = {"人工": True, "转人工": True, "我要投诉": True, "能不能转人工": True, "找真人客服": True,
             "ORD002 晚到太久了，我要投诉": True, "不用转人工了": False, "不用转人工客服": False,
             "你是真人吗？": False, "我不是要投诉，只是问问": False, "人工智能能做什么": False}
    got = {text: wants_person(text) for text in cases}
    assert got == cases, {text: value for text, value in got.items() if value != cases[text]}
    return {"cases": len(cases), "requests": [text for text, value in cases.items() if value]}


def handoff_lifecycle():
    svc = service()
    try:
        with clients(svc) as users:
            say(users, "ORD001")
            post(users["customer"], "/api/customer/confirm", {"answer": "cancel"})
            before = len(runs(users))
            first = say(users, "ORD002 晚到太久了，我要投诉")
            handoff = first["handoff"]
            assert first["outcome"] == "handoff_requested" and first["messages"] == [] and first["created"]
            assert handoff["status"] == "waiting" and handoff["order_id"] == "ORD002", handoff
            logged = runs(users)[before:]
            assert [run["event"] for run in logged] == ["handoff_request"], "The model was asked about a handoff"
            assert logged[0]["via"] == "keyword"
            assert focus(users)["order_id"] == "ORD002", "The panel did not follow the order named in the handoff"
            again = post(users["customer"], "/api/customer/handoff", {})
            assert not again["created"] and again["handoff"]["handoff_id"] == handoff["handoff_id"]
            waiting = say(users, "转人工")
            assert waiting["outcome"] == "handoff_waiting" and waiting["handoff"]["handoff_id"] == handoff["handoff_id"]
            queue = get(users["reviewer"], "/api/review/handoffs")
            assert len(queue["waiting"]) == 1 and queue["closed"] == []
            item = queue["waiting"][0]
            assert item["customer_id"] == "U001" and "thread_id" not in item
            assert item["request_text"] == "ORD002 晚到太久了，我要投诉"
            assert [line["role"] for line in item["excerpt"]] == ["customer", "tool", "assistant", "customer", "assistant"]
            assert item["excerpt"][1]["text"] == "查询 ORD001" and all(len(line["text"]) <= 160 for line in item["excerpt"])
            hid = handoff["handoff_id"]
            for who, status in (("anonymous", 401), ("customer", 401), ("other", 401)):
                post(users[who], f"/api/review/handoffs/{hid}/reply", {"text": "你好"}, status)
            get(users["anonymous"], "/api/review/handoffs", 401)
            post(users["other"], f"/api/customer/handoffs/{hid}/cancel", {}, 404)
            post(users["customer"], "/api/customer/handoffs/H9999/cancel", {}, 404)
            cancelled = post(users["customer"], f"/api/customer/handoffs/{hid}/cancel", {})["handoff"]
            assert cancelled["status"] == "cancelled"
            post(users["customer"], f"/api/customer/handoffs/{hid}/cancel", {}, 409)
            post(users["reviewer"], f"/api/review/handoffs/{hid}/reply", {"text": "晚了"}, 409)
            # A fresh button press after the cancel opens a new one with no typed text.
            second = post(users["customer"], "/api/customer/handoff", {})["handoff"]
            assert second["handoff_id"] != hid and second["request_text"] is None
            sid = second["handoff_id"]
            for text in (None, "", "   ", "回" * 501):
                post(users["reviewer"], f"/api/review/handoffs/{sid}/reply", {"text": text}, 400)
            post(users["reviewer"], "/api/review/handoffs/H9999/reply", {"text": "你好"}, 404)
            answer = "你好，我是人工客服，已看到 ORD002 的情况，我来帮你核对。"
            replied = post(users["reviewer"], f"/api/review/handoffs/{sid}/reply", {"text": answer})["handoff"]
            assert replied["status"] == "replied" and replied["reviewer_id"] == "R001"
            post(users["reviewer"], f"/api/review/handoffs/{sid}/reply", {"text": "再回一次"}, 409)
            post(users["customer"], f"/api/customer/handoffs/{sid}/cancel", {}, 409)
            shown = get(users["customer"], "/api/customer/state")["handoffs"]
            assert [(item["handoff_id"], item["status"]) for item in shown] == [(hid, "cancelled"), (sid, "replied")]
            assert shown[-1]["reply_text"] == answer and all("reviewer_id" not in item for item in shown)
            assert get(users["other"], "/api/customer/state")["handoffs"] == []
            # A typed "no" goes to the AI as a normal message.
            assert say(users, "不用转人工了")["outcome"] == "not_selected"
            events = [run["event"] for run in runs(users)]
            assert events.count("handoff_request") == 4 and "handoff_cancel" in events and "handoff_reply" in events
            # Relogging keeps the answered handoff and drops the cancelled one.
            post(users["customer"], "/api/customer/login", {"customer_id": "U001"})
            again_shown = get(users["customer"], "/api/customer/state")["handoffs"]
            assert [(item["handoff_id"], item["after"]) for item in again_shown] == [(sid, 0)]
            post(users["reviewer"], "/api/review/reset", {})
            assert get(users["reviewer"], "/api/review/handoffs") == {"waiting": [], "closed": []}
            return {"keyword_handoff": hid, "button_handoff": sid, "order_id": handoff["order_id"],
                    "excerpt_lines": len(item["excerpt"]), "events": events}
    finally:
        svc.store.close()


def handoff_limit():
    svc = service()
    saved = ord001_web_service.HANDOFF_LIMIT
    ord001_web_service.HANDOFF_LIMIT = 1
    try:
        with clients(svc) as users:
            post(users["customer"], "/api/customer/handoff", {})
            limited = users["other"].post("/api/customer/handoff", json={})
            assert limited.status_code == 429 and limited.json()["error"] == "handoff_limit"
            return {"limit": 1, "second_customer_http": limited.status_code}
    finally:
        ord001_web_service.HANDOFF_LIMIT = saved
        svc.store.close()


def rating_once():
    svc = service()
    try:
        with clients(svc) as users:
            assert say(users, "ORD001")["confirmation"] is not None
            tid = post(users["customer"], "/api/customer/confirm", {"answer": "confirm"})["ticket"]["ticket_id"]
            url = f"/api/customer/tickets/{tid}/rating"
            post(users["customer"], url, {"rating": 5}, 409)
            post(users["reviewer"], f"/api/review/tickets/{tid}/decision", {"decision": "reject", "note": "演示驳回。"})
            for value in (0, 6, True, "5", 4.5, None):
                post(users["customer"], url, {"rating": value}, 400)
            post(users["other"], url, {"rating": 5}, 404)
            post(users["reviewer"], url, {"rating": 5}, 401)
            rated = post(users["customer"], url, {"rating": 2})
            assert rated["ticket"]["rating"] == 2 and rated["ticket"]["status"] == "rejected"
            assert rated["timeline"][-1] == {"at": rated["timeline"][-1]["at"], "action": "rated", "note": "2 分"}
            post(users["customer"], url, {"rating": 5}, 409)
            decided = get(users["reviewer"], "/api/review/tickets")["decided"]
            assert decided[0]["rating"] == 2 and decided[0]["coupon_issued_yuan"] is None
            logged = [run for run in runs(users) if run["event"] == "customer_rating"]
            assert len(logged) == 1 and logged[0]["rating"] == 2
            return {"ticket_id": tid, "rating": 2, "rejected_values": 6}
    finally:
        svc.store.close()


def reply_guard():
    risky = {
        "放心，保证给你赔 20 元。": "amount",
        "您一定能拿到补偿券的。": "promise",
        "我马上为您退款。": "refund",
        "补偿券已发放到您的账户。": "claim",
        "已经为您转接人工客服。": "claim",
    }
    results = {}
    for text, rule in risky.items():
        svc = service(model=FixedReply(reply=text))
        try:
            with clients(svc) as users:
                turn = say(users, "我的外卖迟到了，能赔多少？")
                shown = [item["text"] for item in turn["messages"] if item["role"] == "assistant"]
                assert shown == [GUARDED_REPLY], shown
                assert turn["reason_code"] == "reply_guarded"
                history = [item["text"] for item in get(users["customer"], "/api/customer/state")["messages"]]
                assert text not in history and GUARDED_REPLY in history
                logged = [run for run in runs(users) if run["event"] == "customer_message"][-1]
                assert logged["guarded"] == {"rule": rule, "text": text}, logged.get("guarded")
                assert get(users["customer"], "/api/customer/state")["tickets"] == []
                results[text] = rule
        finally:
            svc.store.close()
    safe = ["您好！我是配送关怀的 AI 客服，可以帮你查配送和申请晚到补偿。",
            "晚到超过 30 分钟可以申请 ¥10 演示补偿券，由商家审核后决定，我不能保证一定通过。",
            "我不能为你退款，可以帮你核实订单是否符合补偿条件。"]
    for text in safe:
        svc = service(model=FixedReply(reply=text))
        try:
            with clients(svc) as users:
                turn = say(users, "你好")
                shown = [item["text"] for item in turn["messages"] if item["role"] == "assistant"]
                assert shown == [text] and turn["reason_code"] is None, (shown, turn["reason_code"])
                assert "guarded" not in runs(users)[-1]
        finally:
            svc.store.close()
    # Server-written replies (rule results, ticket status) are not checked: they come from the rule itself.
    svc = service()
    try:
        with clients(svc) as users:
            tid = approved_ticket(users)
            reused = say(users, "ORD001")
            assert reused["outcome"] == "ticket_reused" and "补偿券已发放" in reused["messages"][-1]["text"]
            assert reused["reason_code"] is None
    finally:
        svc.store.close()
    return {"replaced": results, "kept": len(safe), "server_template_kept": tid}


PREVIOUS_TICKETS = SCHEMA.split("CREATE TABLE IF NOT EXISTS handoffs", 1)[0].replace(
    "    rating INTEGER,\n    rated_at TEXT,\n", "")


def upgrade_in_place():
    assert "rating" not in PREVIOUS_TICKETS and "information_request" in PREVIOUS_TICKETS
    with tempfile.TemporaryDirectory(prefix="ord001-features-") as directory:
        db_path = Path(directory) / "tickets.sqlite3"
        with sqlite3.connect(db_path) as db:
            db.executescript(PREVIOUS_TICKETS)
            db.execute(
                "INSERT INTO tickets (ticket_id, customer_id, order_id, policy_version, expected_at, delivered_at,"
                " late_seconds, proposed_coupon_yuan, status, coupon_issued_yuan, created_at, decided_at,"
                " reviewer_id, review_note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("T0001", "U001", "ORD001", "demo-v1", "18:00", "18:50", 3000, 10, "approved", 10,
                 "2026-11-11T14:37:00+08:00", "2026-11-11T14:38:17+08:00", "R001", "同意。"))
            db.execute("INSERT INTO ticket_events (event_id, ticket_id, at, actor, action, note) VALUES (?, ?, ?, ?, ?, ?)",
                       (5, "T0001", "2026-11-11T14:38:17+08:00", "reviewer:R001", "approved", "同意。"))
            before = dict(zip([c[1] for c in db.execute("PRAGMA table_info(tickets)")],
                              db.execute("SELECT * FROM tickets").fetchone()))
        for phase in ("upgrade", "restart"):
            svc = service(db_path)
            try:
                with clients(svc) as users:
                    ticket = svc.store.get("T0001")
                    assert {key: ticket[key] for key in before} == before
                    if phase == "upgrade":
                        assert ticket["rating"] is None
                        post(users["customer"], "/api/customer/tickets/T0001/rating", {"rating": 5})
                        post(users["customer"], "/api/customer/handoff", {})
                    else:
                        assert ticket["rating"] == 5
                        assert [item["status"] for item in get(users["reviewer"], "/api/review/handoffs")["waiting"]] == ["waiting"]
                        focus_now = say(users, "ORD001") and focus(users)
                        assert focus_now["ticket_id"] == "T0001"
            finally:
                svc.store.close()
        with sqlite3.connect(db_path) as db:
            assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert db.execute("SELECT COUNT(*) FROM tickets").fetchone()[0] == 1
            actions = [row[0] for row in db.execute("SELECT action FROM ticket_events WHERE ticket_id='T0001' ORDER BY event_id")]
            assert actions == ["approved", "rated"], actions
            event_ids = [row[0] for row in db.execute("SELECT event_id FROM ticket_events ORDER BY event_id")]
            assert event_ids[0] == 5
    return {"ticket_kept": "T0001", "new_columns": ["rating", "rated_at"], "handoffs_table": "created",
            "integrity_check": "ok"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, help="Save the actual result to this JSON file")
    args = parser.parse_args()
    cases = [
        ("申请进度跟随正在咨询的订单；他人订单不显示任何事实", focus_follows_order),
        ("转人工关键词识别（含「不用转人工」等否定）", handoff_words),
        ("转人工：关键词直达不经模型、同一顾客只排一个、取消、人工回复、权限与重置", handoff_lifecycle),
        ("人工咨询总量上限", handoff_limit),
        ("满意度：审核后才能评、1–5 整数、本人一次", rating_once),
        ("AI 回复护栏：金额、承诺、退款、虚假完成被替换并记录；正常回复与服务端模板不受影响", reply_guard),
        ("现有 SQLite 原地加列、建表，保留旧工单和事件，重启后继续", upgrade_in_place),
    ]
    results = []
    for title, check in cases:
        try:
            results.append({"case": title, "status": "passed", "evidence": check()})
        except Exception as exc:
            results.append({"case": title, "status": "failed", "error": f"{type(exc).__name__}: {exc}"})
        print(f"{results[-1]['status']}: {title}", flush=True)
    failed = sum(row["status"] == "failed" for row in results)
    report = {"checked_at": datetime.now().astimezone().isoformat(timespec="seconds"),
              "mode": "in-process TestClient; isolated databases; scripted or fixed-reply model",
              "results": results, "summary": {"passed": len(results) - failed, "failed": failed}}
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False))
    for row in results:
        if row["status"] == "failed":
            print(row["case"], "→", row["error"])
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
