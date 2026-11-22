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

"""Verify human-handoff action panel, RBAC 403 checks, timeline logs, and both reproduction paths."""

import argparse
import json
from contextlib import ExitStack, contextmanager
from urllib.parse import urlsplit

import httpx
from starlette.testclient import TestClient

from ord001_langchain import ScriptedOrderModel
from ord001_web import create_app
from ord001_web_service import DemoService


@contextmanager
def make_clients(base_url: str | None = None):
    svc = None if base_url else DemoService(model=ScriptedOrderModel())
    app = None if base_url else create_app(svc)
    with ExitStack() as stack:
        def open_client():
            if base_url:
                return stack.enter_context(httpx.Client(base_url=base_url, timeout=60))
            return stack.enter_context(TestClient(app))

        users = {
            "customer": open_client(),
            "reviewer": open_client(),
            "supervisor": open_client(),
            "observer": open_client(),
            "anonymous": open_client(),
        }
        assert users["customer"].post("/api/customer/login", json={"customer_id": "U001"}).status_code == 200
        assert users["reviewer"].post("/api/review/login", json={"reviewer_id": "R001"}).status_code == 200
        assert users["supervisor"].post("/api/review/login", json={"reviewer_id": "R002"}).status_code == 200
        assert users["observer"].post("/api/review/login", json={"reviewer_id": "R003"}).status_code == 200
        if base_url:
            assert users["reviewer"].post("/api/review/reset", json={}).status_code == 200
        try:
            yield users
        finally:
            if svc:
                svc.store.close()


def post(client, path: str, body: dict, expected: int = 200) -> dict:
    resp = client.post(path, json=body)
    assert resp.status_code == expected, (path, resp.status_code, resp.text)
    return resp.json()


def get(client, path: str, expected: int = 200) -> dict:
    resp = client.get(path)
    assert resp.status_code == expected, (path, resp.status_code, resp.text)
    return resp.json()


def run_all(base_url: str | None = None) -> dict:
    results = {}
    with make_clients(base_url) as users:
        c, r1, r2, r3, anon = (
            users["customer"], users["reviewer"], users["supervisor"], users["observer"], users["anonymous"]
        )

        # Verify observer role metadata
        me_r3 = get(r3, "/api/review/me")["reviewer"]
        assert me_r3["can_handle"] is False and me_r3["role"] == "observer", me_r3

        # --- Path 1: ORD008 rejected -> second appeal goes straight to human -> agent approves T0001 ¥10 ---
        t1_turn = post(c, "/api/customer/messages", {"text": "我的外卖 ORD008 迟到了，可以申请补偿吗？"})
        assert t1_turn["confirmation"]["order_id"] == "ORD008"
        t1 = post(c, "/api/customer/confirm", {"answer": "confirm"})["ticket"]
        tid1 = t1["ticket_id"]
        assert tid1 == "T0001"
        post(r1, f"/api/review/tickets/{tid1}/decision", {"decision": "reject", "note": "请提供说明"})

        # Second appeal in chat goes directly to human handoff (NOT auto-rejected)
        second_appeal = post(c, "/api/customer/messages", {"text": "二次申请 ORD008 补偿，请人工复核"})
        assert second_appeal["outcome"] == "handoff_requested", second_appeal
        hid1 = second_appeal["handoff"]["handoff_id"]
        assert second_appeal["handoff"]["order_id"] == "ORD008"

        # Observer R003 must get 403 on every mutation endpoint; anonymous & customer get 401
        for action_body in (
            {"action": "approve_compensation", "amount_yuan": 10},
            {"action": "uphold_reject", "note": "越权维持"},
            {"action": "internal_note", "note": "越权备注"},
            {"action": "close_session"},
        ):
            post(r3, f"/api/review/handoffs/{hid1}/action", action_body, expected=403)
            post(anon, f"/api/review/handoffs/{hid1}/action", action_body, expected=401)
            post(c, f"/api/review/handoffs/{hid1}/action", action_body, expected=401)
        post(r3, f"/api/review/handoffs/{hid1}/reply", {"text": "越权回复"}, expected=403)
        post(r3, "/api/review/stp-batch", {}, expected=403)

        # Mandatory reason validation on uphold_reject
        post(r1, f"/api/review/handoffs/{hid1}/action", {"action": "uphold_reject", "note": "   "}, expected=400)

        # Test uphold_reject -> request_info -> customer submit -> escalate -> approve_compensation ¥10 -> close_session
        uphold = post(r1, f"/api/review/handoffs/{hid1}/action", {"action": "uphold_reject", "note": "首次证据不足，维持驳回"})
        assert uphold["ticket"]["status"] == "rejected" and uphold["ticket"]["review_note"] == "首次证据不足，维持驳回"
        assert uphold["handoff"]["status"] == "replied", "Action must move handoff out of waiting"

        req_info = post(r1, f"/api/review/handoffs/{hid1}/action", {"action": "request_info", "note": "请补充外卖袋照片说明"})
        assert req_info["ticket"]["status"] == "needs_info"
        post(c, f"/api/customer/tickets/{tid1}/information", {"text": "已核对门卫签收时间 18:31"})

        esc = post(r1, f"/api/review/handoffs/{hid1}/action", {"action": "escalate", "note": "请主管复核雨天延误"})
        assert esc["handoff"]["escalated_to"] == "主管专席"

        approved = post(r1, f"/api/review/handoffs/{hid1}/action", {"action": "approve_compensation", "amount_yuan": 10})
        assert approved["ticket"]["status"] == "approved" and approved["ticket"]["coupon_issued_yuan"] == 10
        assert approved["action_log"]["before_status"] in ("pending", "rejected", "needs_info")
        assert approved["action_log"]["after_status"] == "approved"

        # Internal note must NOT leak to customer
        secret_note = "内部风控备注：骑手雨天免罚，仅坐席可见"
        post(r1, f"/api/review/handoffs/{hid1}/action", {"action": "internal_note", "note": secret_note})
        post(r1, f"/api/review/handoffs/{hid1}/action", {"action": "close_session", "note": "已完成补偿处理"})

        c_state = get(c, "/api/customer/state")
        c_ticket1 = next(t for t in c_state["tickets"] if t["ticket_id"] == tid1)
        assert c_ticket1["status"] == "approved" and c_ticket1["coupon_issued_yuan"] == 10
        c_handoff1 = next(h for h in c_state["handoffs"] if h["handoff_id"] == hid1)
        assert c_handoff1["ended_at"] is not None
        assert any(e.get("role") == "system" and "¥10" in e.get("text", "") for e in c_handoff1["events"])
        assert secret_note not in json.dumps(c_state, ensure_ascii=False), "Internal note leaked to customer!"
        results["path1_rejected_second_appeal"] = {
            "ticket_id": tid1,
            "handoff_id": hid1,
            "final_ticket_status": c_ticket1["status"],
            "coupon_issued_yuan": c_ticket1["coupon_issued_yuan"],
            "action_logs_count": len(approved["handoff"]["action_logs"]) + 2,
        }

        # --- Path 2: Customer picks order ORD005 and initiates human consultation -> create_ticket -> expedite/transfer -> reject/reopen/approve ---
        h2_res = post(c, "/api/customer/handoff", {"order_id": "ORD005", "text": "咨询订单 ORD005：请人工客服协助处理"})
        hid2 = h2_res["handoff"]["handoff_id"]
        assert h2_res["handoff"]["order_id"] == "ORD005"

        # Urge & create ticket
        urge = post(r1, f"/api/review/handoffs/{hid2}/action", {"action": "urge_or_reassign", "mode": "urge", "note": "优先核对配送"})
        assert urge["action_log"]["action"] == "urge_or_reassign"
        created_t = post(r1, f"/api/review/handoffs/{hid2}/action", {"action": "create_ticket", "amount_yuan": 10})
        tid2 = created_t["ticket"]["ticket_id"]
        assert created_t["ticket"]["status"] == "pending"

        # Pending actions: expedite, transfer, reject (must require reason!)
        post(r1, f"/api/review/handoffs/{hid2}/action", {"action": "expedite", "note": "高峰加急"})
        trans = post(r1, f"/api/review/handoffs/{hid2}/action", {"action": "transfer", "target_reviewer_id": "R002"})
        assert trans["handoff"]["assigned_reviewer_id"] == "R002"
        post(r2, f"/api/review/handoffs/{hid2}/action", {"action": "reject", "note": ""}, expected=400)
        rej2 = post(r2, f"/api/review/handoffs/{hid2}/action", {"action": "reject", "note": "需核验签收门牌"})
        assert rej2["ticket"]["status"] == "rejected" and rej2["handoff"]["status"] == "replied"
        c_t2 = get(c, f"/api/customer/tickets/{tid2}")["ticket"]
        assert c_t2["status"] == "rejected" and c_t2["review_note"] == "需核验签收门牌"

        # Reopen -> approve custom ¥15 -> close session
        reopened = post(r2, f"/api/review/handoffs/{hid2}/action", {"action": "reopen", "note": "顾客补充后重开"})
        assert reopened["ticket"]["status"] == "pending"
        app2 = post(r2, f"/api/review/handoffs/{hid2}/action", {"action": "approve", "amount_yuan": 15, "note": "主管特批 ¥15"})
        assert app2["ticket"]["status"] == "approved" and app2["ticket"]["coupon_issued_yuan"] == 15
        closed2 = post(r2, f"/api/review/handoffs/{hid2}/action", {"action": "close_session"})
        assert closed2["handoff"]["ended_at"] is not None

        # Verify timeline traceability
        logs2 = closed2["handoff"]["action_logs"]
        for entry in logs2:
            assert entry["actor_id"] and entry["at"] and entry["action_label"]
        results["path2_order_handoff"] = {
            "ticket_id": tid2,
            "handoff_id": hid2,
            "final_status": app2["ticket"]["status"],
            "coupon_issued_yuan": app2["ticket"]["coupon_issued_yuan"],
            "timeline_actions": [e["action"] for e in logs2],
        }
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", help="Optional running server base URL (e.g. http://127.0.0.1:8024)")
    args = parser.parse_args()
    if args.base_url:
        parsed = urlsplit(args.base_url)
        if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost"):
            parser.error("--base-url must be local http://127.0.0.1:port or http://localhost:port")
    report = run_all(args.base_url)
    print(json.dumps({"status": "passed", **report}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
