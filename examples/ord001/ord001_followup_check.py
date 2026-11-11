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

"""Re-run the information-request lifecycle in isolated TestClients; never resets a running server."""

import argparse
import json
import sqlite3
import tempfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, contextmanager
from datetime import datetime
from pathlib import Path

from starlette.testclient import TestClient

from ord001_langchain import ScriptedOrderModel
from ord001_web import create_app
from ord001_web_service import DemoService, ServiceError

OLD_SCHEMA = """
CREATE TABLE tickets (
    ticket_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL, order_id TEXT NOT NULL,
    policy_version TEXT NOT NULL, expected_at TEXT NOT NULL, delivered_at TEXT NOT NULL,
    late_seconds INTEGER NOT NULL, proposed_coupon_yuan INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected')),
    coupon_issued_yuan INTEGER, created_at TEXT NOT NULL, decided_at TEXT,
    reviewer_id TEXT, review_note TEXT, UNIQUE (order_id, policy_version)
);
CREATE TABLE ticket_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT, ticket_id TEXT NOT NULL,
    at TEXT NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL, note TEXT
);
"""


def service(path=":memory:"):
    return DemoService(model=ScriptedOrderModel(), db_path=str(path))


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


def get(client, url):
    response = client.get(url)
    assert response.status_code == 200, (url, response.status_code, response.text)
    return response.json()


def create_ticket(users, order_id="ORD005"):
    first = post(users["customer"], "/api/customer/messages", {"text": order_id})
    assert first["confirmation"] is not None
    assert get(users["customer"], "/api/customer/tickets")["tickets"] == []
    ticket = post(users["customer"], "/api/customer/confirm", {"answer": "confirm"})["ticket"]
    assert ticket["status"] == "pending" and ticket["coupon_issued_yuan"] is None
    return ticket


def action(users, tid, decision="request_info", note="请补充收餐时的情况。", expected=200):
    return post(users["reviewer"], f"/api/review/tickets/{tid}/decision",
                {"decision": decision, "note": note}, expected)


def information(users, tid, text="订单放在门口，18:31 取到。", who="customer", expected=200):
    return post(users[who], f"/api/customer/tickets/{tid}/information", {"text": text}, expected)


def facts(ticket):
    return tuple(ticket[key] for key in ("ticket_id", "order_id", "late_seconds", "policy_version", "proposed_coupon_yuan"))


def question_and_review_guards():
    svc = service()
    try:
        with clients(svc) as users:
            ticket = create_ticket(users)
            tid = ticket["ticket_id"]
            for note in (None, "", "   ", "问" * 201):
                action(users, tid, note=note, expected=400)
            url = f"/api/review/tickets/{tid}/decision"
            for who in ("anonymous", "customer", "other"):
                post(users[who], url, {"decision": "request_info", "note": "收餐情况？"}, 401)
            try:
                svc.decide(tid, "U001", "request_info", "收餐情况？")
                raise AssertionError("A customer was accepted as reviewer")
            except ServiceError as exc:
                assert exc.status == 403
            waiting = action(users, tid)["ticket"]
            assert waiting["status"] == "needs_info" and waiting["coupon_issued_yuan"] is None
            assert waiting["decided_at"] is None
            assert waiting["information_request"] == "请补充收餐时的情况。"
            for decision in ("approve", "reject", "request_info"):
                action(users, tid, decision, expected=409)
            queue = get(users["reviewer"], "/api/review/tickets")
            assert len(queue["pending"]) == 1 and queue["pending"][0]["review_request"] is None
            assert queue["decided"] == []
            view = get(users["customer"], f"/api/customer/tickets/{tid}")
            assert "reviewer_id" not in view["ticket"]
            assert all("actor" not in event for event in view["timeline"])
            assert view["timeline"][-1]["note"] == waiting["information_request"]
            return {"ticket_id": tid, "status": waiting["status"], "blocked_decisions": 3}
    finally:
        svc.store.close()


def customer_guards():
    svc = service()
    try:
        with clients(svc) as users:
            ticket = create_ticket(users)
            tid = ticket["ticket_id"]
            information(users, tid, expected=409)
            action(users, tid)
            information(users, tid, who="anonymous", expected=401)
            information(users, tid, who="reviewer", expected=401)
            other_ticket = information(users, tid, who="other", expected=404)
            missing_ticket = information(users, "T9999", expected=404)
            assert other_ticket == missing_ticket, "Missing and unowned tickets must look the same to the customer"
            for text in (None, "", "  ", [], "字" * 501):
                information(users, tid, text=text, expected=400)
            detail = information(users, tid)
            assert facts(detail["ticket"]) == facts(ticket)
            assert detail["ticket"]["status"] == "pending"
            assert detail["ticket"]["coupon_issued_yuan"] is None
            assert detail["ticket"]["customer_information"] == "订单放在门口，18:31 取到。"
            information(users, tid, expected=409)
            request = get(users["reviewer"], "/api/review/tickets")["pending"][0]["review_request"]
            assert request["customer_information"] == detail["ticket"]["customer_information"]
            return {"ticket_id": tid, "status": detail["ticket"]["status"], "ownership_http": 404,
                    "duplicate_http": 409, "late_seconds": detail["ticket"]["late_seconds"]}
    finally:
        svc.store.close()


def multiple_rounds_approve():
    svc = service()
    try:
        with clients(svc) as users:
            ticket = create_ticket(users)
            tid = ticket["ticket_id"]
            for question, answer in (("请说明取餐情况。", "18:31 在门口取到。"),
                                     ("是否有其他配送备注？", "已核对，订单备注为放门口。")):
                waiting = action(users, tid, note=question)["ticket"]
                assert facts(waiting) == facts(ticket) and waiting["customer_information"] is None
                assert waiting["coupon_issued_yuan"] is None
                reused = post(users["customer"], "/api/customer/messages", {"text": "ORD005"})
                assert reused["outcome"] == "ticket_reused" and reused["ticket"]["ticket_id"] == tid
                assert "待补充" in "".join(item["text"] for item in reused["messages"])
                sent = information(users, tid, answer)["ticket"]
                assert facts(sent) == facts(ticket) and sent["coupon_issued_yuan"] is None
            final = action(users, tid, "approve", "补充情况已核实。")
            assert final["ticket"]["coupon_issued_yuan"] == 10 and final["ticket"]["status"] == "approved"
            assert facts(final["ticket"]) == facts(ticket)
            expected = ["submitted", "information_requested", "information_submitted",
                        "information_requested", "information_submitted", "approved"]
            assert [event["action"] for event in final["events"]] == expected
            assert len(get(users["customer"], "/api/customer/tickets")["tickets"]) == 1
            action(users, tid, "approve", expected=409)
            information(users, tid, expected=409)
            view = get(users["customer"], f"/api/customer/tickets/{tid}")
            assert view["ticket"]["review_note"] == "补充情况已核实。" and "reviewer_id" not in view["ticket"]
            return {"ticket_id": tid, "events": expected, "late_seconds": final["ticket"]["late_seconds"],
                    "coupon_issued_yuan": final["ticket"]["coupon_issued_yuan"]}
    finally:
        svc.store.close()


def reject_after_information():
    svc = service()
    try:
        with clients(svc) as users:
            ticket = create_ticket(users, "ORD001")
            tid = ticket["ticket_id"]
            action(users, tid)
            information(users, tid)
            final = action(users, tid, "reject", "已查阅补充，本次不发券。")
            assert final["ticket"]["status"] == "rejected" and final["ticket"]["coupon_issued_yuan"] is None
            assert facts(final["ticket"]) == facts(ticket)
            assert [event["action"] for event in final["events"]] == [
                "submitted", "information_requested", "information_submitted", "rejected"]
            return {"status": "rejected", "coupon_issued_yuan": None}
    finally:
        svc.store.close()


def concurrent_retries():
    svc = service()
    try:
        with clients(svc) as users:
            tid = create_ticket(users)["ticket_id"]
            action(users, tid)
            def reply_once(_):
                try:
                    svc.submit_information("U001", tid, "并发重试同一份补充。")
                    return 200
                except ServiceError as exc:
                    return exc.status
            with ThreadPoolExecutor(max_workers=2) as pool:
                replies = sorted(pool.map(reply_once, range(2)))
            assert replies == [200, 409]
            def approve_once(_):
                try:
                    svc.decide(tid, "R001", "approve", "已核实。")
                    return 200
                except ServiceError as exc:
                    return exc.status
            with ThreadPoolExecutor(max_workers=2) as pool:
                decisions = sorted(pool.map(approve_once, range(2)))
            assert decisions == [200, 409]
            events = svc.store.events(tid)
            assert [event["action"] for event in events].count("information_submitted") == 1
            assert [event["action"] for event in events].count("approved") == 1
            return {"reply_http": replies, "approval_http": decisions,
                    "coupon_issued_yuan": svc.store.get(tid)["coupon_issued_yuan"]}
    finally:
        svc.store.close()


def migrate_and_restart():
    with tempfile.TemporaryDirectory(prefix="ord001-followup-") as directory:
        db_path = Path(directory) / "tickets.sqlite3"
        with sqlite3.connect(db_path) as db:
            db.executescript(OLD_SCHEMA)
            db.execute("INSERT INTO tickets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       ("T0001", "U001", "ORD005", "demo-v1", "18:00", "18:30:01", 1801, 10,
                        "pending", None, "2026-11-10T18:31:00+08:00", None, None, None))
            db.execute("INSERT INTO tickets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       ("T0002", "U001", "ORD001", "demo-v1", "18:00", "18:50", 3000, 10,
                        "approved", 10, "2026-11-10T18:51:00+08:00", "2026-11-10T18:52:00+08:00",
                        "R001", "旧审核说明"))
            db.executemany("INSERT INTO ticket_events VALUES (?, ?, ?, ?, ?, ?)", [
                (7, "T0001", "2026-11-10T18:31:00+08:00", "customer:U001", "submitted", None),
                (8, "T0002", "2026-11-10T18:51:00+08:00", "customer:U001", "submitted", None),
                (9, "T0002", "2026-11-10T18:52:00+08:00", "reviewer:R001", "approved", "旧审核说明"),
            ])
        original = None
        for phase in ("migration", "waiting_restart", "pending_restart"):
            svc = service(db_path)
            try:
                with clients(svc) as users:
                    old = svc.store.get("T0002")
                    assert old["status"] == "approved" and old["coupon_issued_yuan"] == 10
                    assert old["review_note"] == "旧审核说明" and old["decided_at"] == "2026-11-10T18:52:00+08:00"
                    assert len(svc.store.events("T0002")) == 2
                    ticket = svc.store.get("T0001")
                    if original is None:
                        original = facts(ticket)
                    assert facts(ticket) == original
                    queue = get(users["reviewer"], "/api/review/tickets")
                    assert len(queue["pending"]) == 1 and len(queue["decided"]) == 1
                    if phase == "migration":
                        assert ticket["information_request"] is None and ticket["customer_information"] is None
                        action(users, "T0001", note="重启后请继续补充收餐情况。")
                    elif phase == "waiting_restart":
                        assert ticket["status"] == "needs_info" and queue["pending"][0]["review_request"] is None
                        assert ticket["information_request"] == "重启后请继续补充收餐情况。"
                        information(users, "T0001", "重启后补充：18:31 在门口取到。")
                    else:
                        assert ticket["status"] == "pending" and queue["pending"][0]["review_request"] is not None
                        assert ticket["customer_information"] == "重启后补充：18:31 在门口取到。"
                        final = action(users, "T0001", "approve", "重启后已核实。")
                        assert final["ticket"]["coupon_issued_yuan"] == 10
                        assert facts(final["ticket"]) == original
            finally:
                svc.store.close()
        with sqlite3.connect(db_path) as db:
            assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            rows = db.execute("SELECT event_id, action FROM ticket_events WHERE ticket_id = 'T0001' ORDER BY event_id").fetchall()
            assert rows[0] == (7, "submitted")
            assert [row[1] for row in rows] == ["submitted", "information_requested", "information_submitted", "approved"]
            assert rows[1][0] > 9
            assert db.execute("SELECT COUNT(*) FROM tickets").fetchone()[0] == 2
            assert "needs_info" in db.execute("SELECT sql FROM sqlite_master WHERE name='tickets'").fetchone()[0]
        return {"legacy_tickets_preserved": 2, "legacy_event_ids_preserved": [7, 8, 9],
                "restart_states": ["needs_info", "pending"], "integrity_check": "ok", "late_seconds": 1801}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, help="Save the actual result to this JSON file")
    args = parser.parse_args()
    results = []
    cases = [
        ("商家问题必填、审批权限与等待补充保护", question_and_review_guards),
        ("顾客归属、文本边界、重复回复与审核恢复", customer_guards),
        ("两轮补充同一申请、原始事实不变、批准后发券", multiple_rounds_approve),
        ("补充后拒绝不发券", reject_after_information),
        ("并发回复和审批只生效一次", concurrent_retries),
        ("旧 SQLite 无损升级、两种状态重启后继续审核", migrate_and_restart),
    ]
    for title, check in cases:
        try:
            evidence = check()
            results.append({"case": title, "status": "passed", "evidence": evidence})
        except Exception as exc:
            results.append({"case": title, "status": "failed", "error": f"{type(exc).__name__}: {exc}"})
    failed = sum(row["status"] == "failed" for row in results)
    report = {"checked_at": datetime.now().astimezone().isoformat(timespec="seconds"),
              "mode": "in-process TestClient; isolated temporary databases; scripted model",
              "results": results, "summary": {"passed": len(results) - failed, "failed": failed}}
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
