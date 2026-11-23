# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = [
#     "langgraph==1.2.19",
#     "langchain==1.4.9",
#     "langchain-openai==1.7.4",
#     "starlette==1.10.0",
#     "httpx==0.28.1",
#     "python-multipart==0.0.20",
# ]
# ///

"""Verification suite for human-review-v1 nine boundary groups (HR01-HR09) + Mode B/C shared guard parity."""

import argparse
import json
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

from langchain_core.messages import AIMessage, SystemMessage
from starlette.testclient import TestClient

from ord001_policy import load_policy
from ord001_web import create_app
from ord001_web_service import DemoService, ServiceError
from ord001_web_store import DemoData, now_text

HERE = Path(__file__).resolve().parent
HR06_FIXTURE = HERE / "fixtures" / "hr06-isolated-data.json"


class DeterministicModeBTestAdapter:
    """Explicit test-only Mode B adapter (supports_mode_b=True) to verify shared guards offline without claiming live LLM."""

    _llm_type = "mode-b-test-adapter"
    supports_mode_b = True

    def __init__(self, forced_amount: int | float | None = 10, force_eligible: bool | None = None):
        self.forced_amount = forced_amount
        self.force_eligible = force_eligible

    def bind_tools(self, tools, **kwargs):
        return self

    def invoke(self, messages):
        sys_txt = messages[0].content if messages and isinstance(messages[0], SystemMessage) else ""
        last_txt = messages[-1].content if messages else ""
        if "只输出一个合法 JSON 对象" in sys_txt:
            import re
            m = re.search(r'"order_id":\s*"(ORD\d+)"', last_txt)
            oid = m.group(1) if m else "ORD001"
            late_m = re.search(r'"late_seconds":\s*(\d+)', last_txt)
            late_sec = int(late_m.group(1)) if late_m else 0
            elig = self.force_eligible if self.force_eligible is not None else (late_sec > 1800)
            payload = {
                "eligible": elig,
                "next_action": "propose_confirm" if elig else "explain_ineligible",
                "order_id": oid,
                "proposed_coupon_yuan": self.forced_amount if elig else None,
                "reason": "adapter_test",
                "reply": f"已核实订单 {oid} 情况，请确认是否提交申请。" if elig else f"订单 {oid} 暂不符合超时补偿条件。",
            }
            return AIMessage(content=json.dumps(payload, ensure_ascii=False))
        import re
        m = re.search(r"(ORD\d+)", last_txt, re.IGNORECASE)
        if m:
            oid = m.group(1).upper()
            return AIMessage(
                content="",
                tool_calls=[{"name": "query_order", "args": {"order_id": oid, "purpose": "compensation"},
                             "id": f"call_{oid}", "type": "tool_call"}],
            )
        return AIMessage(content="请提供订单号以便核实。")


def make_env(*, db_path=":memory:", data_path: Path | None = None, policy=None,
             agent_mode: str = "C", model=None, model_config_path: str | None = None):
    data = DemoData(data_path) if data_path else DemoData()
    svc = DemoService(
        db_path=db_path,
        data=data,
        policy=policy or load_policy(),
        agent_mode=agent_mode,
        model=model,
        model_config_path=model_config_path,
    )
    app = create_app(svc)
    return svc, app


def login_client(app, role: str, user_id: str) -> TestClient:
    c = TestClient(app)
    if role == "customer":
        r = c.post("/api/customer/login", json={"customer_id": user_id})
    else:
        r = c.post("/api/review/login", json={"reviewer_id": user_id})
    assert r.status_code == 200, r.text
    return c


def submit_claim_via_chat(cust: TestClient, order_id: str) -> dict:
    r1 = cust.post("/api/customer/messages", json={"text": f"{order_id} 迟到了申请补偿"})
    assert r1.status_code == 200, r1.text
    d1 = r1.json()
    assert d1["outcome"] == "awaiting_confirmation", d1
    r2 = cust.post("/api/customer/confirm", json={"answer": "confirm"})
    assert r2.status_code == 200, r2.text
    d2 = r2.json()
    assert d2["outcome"] == "ticket_created", d2
    return d2["ticket"]


def check_hr01(model_config: str | None) -> dict:
    """HR01: Valid reconsideration with verifiable_relevant_new_information & prior_processing_error along original ticket."""
    svc, app = make_env(model_config_path=model_config)
    try:
        u1 = login_client(app, "customer", "U001")
        r1 = login_client(app, "reviewer", "R001")
        r2 = login_client(app, "reviewer", "R002")
        t = submit_claim_via_chat(u1, "ORD001")
        tid = t["ticket_id"]

        rej1 = r1.post(f"/api/review/tickets/{tid}/decision", json={"decision": "reject", "note": "首次判断：临时交通管制不予补偿"})
        assert rej1.status_code == 200 and rej1.json()["ticket"]["status"] == "rejected"

        # Case A: Direct reopen endpoint with verifiable_relevant_new_information -> restores pending (NOT auto-approved!)
        reop1 = r1.post(
            f"/api/review/tickets/{tid}/reopen",
            json={
                "reason_type": "verifiable_relevant_new_information",
                "note": "顾客补充门禁监控截图，核实实际晚到50分钟非管制路段",
            },
        )
        assert reop1.status_code == 200, reop1.text
        body1 = reop1.json()
        assert body1["ticket"]["ticket_id"] == tid
        assert body1["ticket"]["status"] == "pending"
        assert body1["ticket"]["coupon_issued_yuan"] is None
        assert body1["ticket"]["prior_review_note"] == "首次判断：临时交通管制不予补偿"
        assert len(svc.store.tickets()) == 1

        # Reject a second time, then test Case B: Handoff reopen with prior_processing_error
        rej2 = r1.post(f"/api/review/tickets/{tid}/decision", json={"decision": "reject", "note": "二次核对仍误按旧时间算"})
        assert rej2.status_code == 200 and rej2.json()["ticket"]["status"] == "rejected"

        h_open = u1.post("/api/customer/handoff", json={"order_id": "ORD001", "text": "你们算错预计送达时间了，请复核"})
        assert h_open.status_code == 200
        hid = h_open.json()["handoff"]["handoff_id"]

        reop2 = r2.post(
            f"/api/review/handoffs/{hid}/action",
            json={
                "action": "reopen",
                "reason_type": "prior_processing_error",
                "note": "客服核实此前误看预计时间，属原处理规则套用错误，沿原工单重审",
            },
        )
        assert reop2.status_code == 200, reop2.text
        t_after = reop2.json()["ticket"]
        assert t_after["ticket_id"] == tid
        assert t_after["status"] == "pending"
        assert t_after["coupon_issued_yuan"] is None
        events = svc.store.events(tid)
        actions = [e["action"] for e in events]
        assert actions.count("rejected") == 2 and actions.count("reopened") == 2
        assert len(svc.store.tickets()) == 1
        return {
            "ticket_id": tid,
            "handoff_id": hid,
            "total_tickets_for_order": len(svc.store.tickets()),
            "prior_review_note_preserved": t_after["prior_review_note"],
            "event_actions": actions,
            "reason_types_recorded": [e.get("reason_type") for e in events if e["action"] == "reopened"],
        }
    finally:
        svc.store.close()


def check_hr02(model_config: str | None) -> dict:
    """HR02: Dissatisfaction alone never auto-reopens; empty reason or invalid reason_type is rejected."""
    svc, app = make_env(model_config_path=model_config)
    try:
        u1 = login_client(app, "customer", "U001")
        r1 = login_client(app, "reviewer", "R001")
        t = submit_claim_via_chat(u1, "ORD001")
        tid = t["ticket_id"]
        r1.post(f"/api/review/tickets/{tid}/decision", json={"decision": "reject", "note": "系统核实不在本次补偿范围"})

        # Customer repeatedly expresses dissatisfaction / asks to re-apply without new verifiable facts
        m1 = u1.post("/api/customer/messages", json={"text": "我对ORD001驳回非常不满意，我要重新申请！"})
        m2 = u1.post("/api/customer/messages", json={"text": "还是不满意，快给我重开申请！"})
        assert m1.status_code == 200 and m2.status_code == 200
        t_now = svc.store.get(tid)
        assert t_now["status"] == "rejected" and len(svc.store.tickets()) == 1

        hid = m1.json()["handoff"]["handoff_id"]
        # Reviewer explains and upholds rejection
        uphold = r1.post(
            f"/api/review/handoffs/{hid}/action",
            json={"action": "uphold_reject", "note": "已再次为您核对履约记录，因暂无可核实新信息维持原驳回结论。"},
        )
        assert uphold.status_code == 200 and uphold.json()["ticket"]["status"] == "rejected"

        # Empty reason reopen attempts must fail with 400
        empty_direct = r1.post(f"/api/review/tickets/{tid}/reopen", json={"note": "   "})
        empty_handoff = r1.post(f"/api/review/handoffs/{hid}/action", json={"action": "reopen", "note": ""})
        bad_reason = r1.post(
            f"/api/review/tickets/{tid}/reopen",
            json={"note": "顾客一直投诉不满意", "reason_type": "dissatisfaction_only"},
        )
        empty_override = r1.post(
            f"/api/review/handoffs/{hid}/action",
            json={"action": "approve_compensation", "note": ""},
        )
        assert empty_direct.status_code == 400
        assert empty_handoff.status_code == 400
        assert bad_reason.status_code == 400
        assert empty_override.status_code == 400
        assert svc.store.get(tid)["status"] == "rejected"
        return {
            "auto_reopened_on_dissatisfaction": False,
            "ticket_status_after_complaints": svc.store.get(tid)["status"],
            "empty_direct_reopen_http": empty_direct.status_code,
            "empty_handoff_reopen_http": empty_handoff.status_code,
            "dissatisfaction_reason_type_http": bad_reason.status_code,
            "empty_override_approve_http": empty_override.status_code,
        }
    finally:
        svc.store.close()


def check_hr03(model_config: str | None) -> dict:
    """HR03: Reopen disallowed on non-rejected states; post-issue reopen/amount-change/top-up blocked."""
    svc, app = make_env(model_config_path=model_config)
    try:
        u1 = login_client(app, "customer", "U001")
        r1 = login_client(app, "reviewer", "R001")
        r2 = login_client(app, "reviewer", "R002")
        t = submit_claim_via_chat(u1, "ORD001")
        tid = t["ticket_id"]

        # 1. Reopen on pending -> 409
        reop_pending = r1.post(f"/api/review/tickets/{tid}/reopen", json={"note": "尝试对pending重审"})
        assert reop_pending.status_code == 409

        # 2. Move to needs_info -> reopen on needs_info -> 409
        r1.post(f"/api/review/tickets/{tid}/decision", json={"decision": "request_info", "note": "请补充门牌照"})
        reop_needs = r1.post(f"/api/review/tickets/{tid}/reopen", json={"note": "尝试对needs_info重审"})
        assert reop_needs.status_code == 409

        # Customer submits info -> R001 approves standard ¥10
        u1.post(f"/api/customer/tickets/{tid}/information", json={"text": "门牌为802室"})
        app_ok = r1.post(f"/api/review/tickets/{tid}/decision", json={"decision": "approve", "note": "核实通过"})
        assert app_ok.status_code == 200 and app_ok.json()["ticket"]["coupon_issued_yuan"] == 10

        h_open = u1.post("/api/customer/handoff", json={"order_id": "ORD001", "text": "10元太少了，能补差价到18元吗？"})
        hid = h_open.json()["handoff"]["handoff_id"]

        # 3. Post-issue reopen, change_amount, top_up, supervisor re-approve at 18, reject -> all 409, amount stays 10!
        reop_app1 = r2.post(f"/api/review/tickets/{tid}/reopen", json={"note": "已发券尝试重开"})
        reop_app2 = r2.post(f"/api/review/handoffs/{hid}/action", json={"action": "reopen", "note": "已发券尝试重开"})
        chg_amt = r2.post(f"/api/review/handoffs/{hid}/action", json={"action": "change_amount", "amount_yuan": 18, "note": "改额"})
        top_up = r2.post(f"/api/review/handoffs/{hid}/action", json={"action": "top_up", "amount_yuan": 8, "note": "补差价"})
        re_decide_18 = r2.post(f"/api/review/tickets/{tid}/decision", json={"decision": "approve", "amount_yuan": 18, "note": "主管试图改成18"})
        flip_reject = r2.post(f"/api/review/tickets/{tid}/decision", json={"decision": "reject", "note": "试图撤回"})

        for resp in (reop_app1, reop_app2, chg_amt, top_up, re_decide_18, flip_reject):
            assert resp.status_code == 409, resp.text
        final_t = svc.store.get(tid)
        assert final_t["status"] == "approved" and final_t["coupon_issued_yuan"] == 10
        assert [e["action"] for e in svc.store.events(tid)].count("approved") == 1
        return {
            "reopen_on_pending_http": reop_pending.status_code,
            "reopen_on_needs_info_http": reop_needs.status_code,
            "reopen_on_approved_http": [reop_app1.status_code, reop_app2.status_code],
            "change_amount_http": chg_amt.status_code,
            "top_up_http": top_up.status_code,
            "supervisor_post_issue_18_http": re_decide_18.status_code,
            "final_coupon_issued_yuan": final_t["coupon_issued_yuan"],
        }
    finally:
        svc.store.close()


def check_hr04(model_config: str | None) -> dict:
    """HR04: Role permissions across direct review, handoff actions, observer R003, customer & AI."""
    svc, app = make_env(model_config_path=model_config)
    try:
        u1 = login_client(app, "customer", "U001")
        r1 = login_client(app, "reviewer", "R001")
        r2 = login_client(app, "reviewer", "R002")
        r3 = login_client(app, "reviewer", "R003")

        t1 = submit_claim_via_chat(u1, "ORD001")
        tid1 = t1["ticket_id"]
        h1 = u1.post("/api/customer/handoff", json={"order_id": "ORD001", "text": "人工处理ORD001"}).json()["handoff"]["handoff_id"]
        h2 = u1.post("/api/customer/handoff", json={"order_id": "ORD008", "text": "人工处理ORD008"}).json()["handoff"]["handoff_id"]

        # R001 attempts custom 15 yuan across all endpoints -> 403
        r1_direct_15 = r1.post(f"/api/review/tickets/{tid1}/decision", json={"decision": "approve", "amount_yuan": 15, "note": "R001改15"})
        r1_handoff_15 = r1.post(f"/api/review/handoffs/{h1}/action", json={"action": "approve", "amount_yuan": 15, "note": "R001改15"})
        r1_create_15 = r1.post(f"/api/review/handoffs/{h2}/action", json={"action": "create_ticket", "amount_yuan": 15, "note": "R001建单15"})
        assert r1_direct_15.status_code == 403
        assert r1_handoff_15.status_code == 403
        assert r1_create_15.status_code == 403

        # R003 read-only observer -> 403
        r3_decide = r3.post(f"/api/review/tickets/{tid1}/decision", json={"decision": "approve", "note": "观察员审批"})
        r3_handoff = r3.post(f"/api/review/handoffs/{h1}/action", json={"action": "approve", "note": "观察员动作"})
        assert r3_decide.status_code == 403 and r3_handoff.status_code == 403

        # Customer session attempting reviewer endpoint -> 401
        cust_write = u1.post(f"/api/review/tickets/{tid1}/decision", json={"decision": "approve", "amount_yuan": 20})
        assert cust_write.status_code == 401

        # R001 standard ¥10 succeeds on ORD001
        r1_std_10 = r1.post(f"/api/review/tickets/{tid1}/decision", json={"decision": "approve", "note": "R001按标准10元通过"})
        assert r1_std_10.status_code == 200 and r1_std_10.json()["ticket"]["coupon_issued_yuan"] == 10

        # R002 custom ¥15 with written reason succeeds on ORD008
        r2_custom_15 = r2.post(
            f"/api/review/handoffs/{h2}/action",
            json={"action": "approve_compensation", "amount_yuan": 15, "note": "阵雨延误且汤洒，主管特批15元"},
        )
        assert r2_custom_15.status_code == 200 and r2_custom_15.json()["ticket"]["coupon_issued_yuan"] == 15

        # AI Mode B unauthorized custom amount proposal (e.g. 18 yuan) is blocked by shared guard
        svc_b, _ = make_env(agent_mode="B", model=DeterministicModeBTestAdapter(forced_amount=18))
        try:
            turn_b = svc_b.send_message("t-b-amt", "U001", "ORD001 赔我18元")
            assert turn_b["confirmation"] is None
            assert turn_b["safety_intercept"] == "unauthorized_amount_blocked"
        finally:
            svc_b.store.close()

        return {
            "r001_custom_15_http": [r1_direct_15.status_code, r1_handoff_15.status_code, r1_create_15.status_code],
            "r003_write_http": [r3_decide.status_code, r3_handoff.status_code],
            "customer_write_http": cust_write.status_code,
            "r001_standard_10_issued": r1_std_10.json()["ticket"]["coupon_issued_yuan"],
            "r002_custom_15_issued": r2_custom_15.json()["ticket"]["coupon_issued_yuan"],
            "ai_custom_amount_intercept": "unauthorized_amount_blocked",
        }
    finally:
        svc.store.close()


def check_hr05(model_config: str | None) -> dict:
    """HR05: Integer 1..20 range, no silent rounding/clamping, mandatory reason for custom amounts."""
    svc, app = make_env(model_config_path=model_config)
    try:
        u1 = login_client(app, "customer", "U001")
        r1 = login_client(app, "reviewer", "R001")
        r2 = login_client(app, "reviewer", "R002")

        t1 = submit_claim_via_chat(u1, "ORD001")  # paid ¥58
        t5 = submit_claim_via_chat(u1, "ORD005")  # paid ¥39
        t8 = submit_claim_via_chat(u1, "ORD008")  # paid ¥36

        invalid_statuses = {}
        for label, bad_amt, note in [
            ("zero", 0, "测试0元"),
            ("twenty_one", 21, "测试21元"),
            ("float_1_5", 1.5, "测试1.5元"),
            ("str_decimal", "10.5", "测试字符串小数"),
            ("empty_reason_custom_15", 15, "   "),
        ]:
            resp = r2.post(
                f"/api/review/tickets/{t1['ticket_id']}/decision",
                json={"decision": "approve", "amount_yuan": bad_amt, "note": note},
            )
            assert resp.status_code == 400, (label, resp.status_code, resp.text)
            invalid_statuses[label] = resp.status_code
        assert svc.store.get(t1["ticket_id"])["coupon_issued_yuan"] is None

        # Valid boundaries: R002 -> 1 yuan on ORD001; R002 -> 20 yuan on ORD005; R001 -> 10 yuan on ORD008
        ok_1 = r2.post(
            f"/api/review/tickets/{t1['ticket_id']}/decision",
            json={"decision": "approve", "amount_yuan": 1, "note": "顾客仅需1元象征补偿，主管核准"},
        )
        ok_20 = r2.post(
            f"/api/review/tickets/{t5['ticket_id']}/decision",
            json={"decision": "approve", "amount_yuan": 20, "note": "严重影响用餐，主管按演示上限核准20元"},
        )
        ok_10 = r1.post(
            f"/api/review/tickets/{t8['ticket_id']}/decision",
            json={"decision": "approve", "note": ""},
        )
        assert ok_1.status_code == 200 and ok_1.json()["ticket"]["coupon_issued_yuan"] == 1
        assert ok_20.status_code == 200 and ok_20.json()["ticket"]["coupon_issued_yuan"] == 20
        assert ok_10.status_code == 200 and ok_10.json()["ticket"]["coupon_issued_yuan"] == 10
        return {
            "invalid_inputs_http": invalid_statuses,
            "valid_supervisor_min_1": ok_1.json()["ticket"]["coupon_issued_yuan"],
            "valid_supervisor_max_20": ok_20.json()["ticket"]["coupon_issued_yuan"],
            "valid_agent_std_10": ok_10.json()["ticket"]["coupon_issued_yuan"],
        }
    finally:
        svc.store.close()


def check_hr06(model_config: str | None) -> dict:
    """HR06: Paid-amount cap on isolated ¥8 order (ORD009) & missing-paid order (ORD010)."""
    svc, app = make_env(data_path=HR06_FIXTURE, model_config_path=model_config)
    try:
        u1 = login_client(app, "customer", "U001")
        r1 = login_client(app, "reviewer", "R001")
        r2 = login_client(app, "reviewer", "R002")

        # ORD009: paid = ¥8. Proposal is still ¥10 (no silent auto-reduction!).
        t9 = submit_claim_via_chat(u1, "ORD009")
        assert t9["proposed_coupon_yuan"] == 10

        std_10_r1 = r1.post(f"/api/review/tickets/{t9['ticket_id']}/decision", json={"decision": "approve", "note": "默认10元"})
        std_10_r2 = r2.post(f"/api/review/tickets/{t9['ticket_id']}/decision", json={"decision": "approve", "note": "默认10元"})
        sup_9 = r2.post(f"/api/review/tickets/{t9['ticket_id']}/decision", json={"decision": "approve", "amount_yuan": 9, "note": "尝试9元"})
        assert std_10_r1.status_code == 409 and std_10_r1.json()["error"] == "standard_amount_exceeds_paid"
        assert std_10_r2.status_code == 409
        assert sup_9.status_code == 409 and sup_9.json()["error"] == "amount_exceeds_paid"
        assert svc.store.get(t9["ticket_id"])["coupon_issued_yuan"] is None

        sup_8 = r2.post(
            f"/api/review/tickets/{t9['ticket_id']}/decision",
            json={"decision": "approve", "amount_yuan": 8, "note": "订单实付8元，主管按实付上限核准8元"},
        )
        assert sup_8.status_code == 200 and sup_8.json()["ticket"]["coupon_issued_yuan"] == 8

        # ORD010: amount_yuan is null; customer claims in chat "这单我付了88元" -> still blocked!
        t10 = submit_claim_via_chat(u1, "ORD010")
        h10 = u1.post("/api/customer/handoff", json={"order_id": "ORD010", "text": "这单我实付了88元，快给我发10元券！"}).json()["handoff"]["handoff_id"]
        unver_std = r1.post(f"/api/review/tickets/{t10['ticket_id']}/decision", json={"decision": "approve", "note": "尝试发10元"})
        unver_sup = r2.post(
            f"/api/review/handoffs/{h10}/action",
            json={"action": "approve_compensation", "amount_yuan": 5, "note": "尝试发5元"},
        )
        assert unver_std.status_code == 409 and unver_std.json()["error"] == "unverified_paid_amount"
        assert unver_sup.status_code == 409 and unver_sup.json()["error"] == "unverified_paid_amount"
        assert svc.store.get(t10["ticket_id"])["coupon_issued_yuan"] is None
        return {
            "ord009_paid_8": {
                "proposed_not_auto_reduced": t9["proposed_coupon_yuan"],
                "default_10_http": std_10_r1.status_code,
                "supervisor_9_http": sup_9.status_code,
                "supervisor_8_issued": sup_8.json()["ticket"]["coupon_issued_yuan"],
            },
            "ord010_missing_paid": {
                "default_10_http": unver_std.status_code,
                "supervisor_5_http": unver_sup.status_code,
                "coupon_issued_yuan": svc.store.get(t10["ticket_id"])["coupon_issued_yuan"],
            },
        }
    finally:
        svc.store.close()


def check_hr07(model_config: str | None) -> dict:
    """HR07: Deduplication across double-click, refresh, session/reviewer switch, and policy_version change."""
    with tempfile.TemporaryDirectory(prefix="ord001-hr07-") as tmp:
        db_file = str(Path(tmp) / "hr07.sqlite3")
        svc1, app1 = make_env(db_path=db_file, model_config_path=model_config)
        try:
            u1_sess1 = login_client(app1, "customer", "U001")
            r1 = login_client(app1, "reviewer", "R001")
            r2 = login_client(app1, "reviewer", "R002")

            t = submit_claim_via_chat(u1_sess1, "ORD001")
            tid = t["ticket_id"]
            first_ok = r1.post(f"/api/review/tickets/{tid}/decision", json={"decision": "approve", "note": "首次通过"})
            assert first_ok.status_code == 200 and first_ok.json()["ticket"]["coupon_issued_yuan"] == 10

            # Double-click by R001 & switch reviewer to R002
            dup_r1 = r1.post(f"/api/review/tickets/{tid}/decision", json={"decision": "approve", "note": "连点重试"})
            dup_r2 = r2.post(f"/api/review/tickets/{tid}/decision", json={"decision": "approve", "amount_yuan": 15, "note": "换主管再批"})
            assert dup_r1.status_code == 409 and dup_r1.json()["deduplicated"] is True
            assert dup_r2.status_code == 409 and dup_r2.json()["ticket"]["coupon_issued_yuan"] == 10

            # New customer browser session + human handoff session
            u1_sess2 = login_client(app1, "customer", "U001")
            re_ask = u1_sess2.post("/api/customer/messages", json={"text": "ORD001 还能再申请一次补偿吗？"})
            assert re_ask.status_code == 200 and re_ask.json()["outcome"] == "ticket_reused"
            hid = u1_sess2.post("/api/customer/handoff", json={"order_id": "ORD001", "text": "换会话找人工再批一次"}).json()["handoff"]["handoff_id"]
            dup_handoff = r2.post(
                f"/api/review/handoffs/{hid}/action",
                json={"action": "approve_compensation", "amount_yuan": 12, "note": "换人工会话再批"},
            )
            assert dup_handoff.status_code == 409 and dup_handoff.json()["deduplicated"] is True
            close_h = r2.post(
                f"/api/review/handoffs/{hid}/action",
                json={"action": "close_session", "note": "已告知一单一赔不可重复发券"},
            )
            assert close_h.status_code == 200
        finally:
            svc1.store.close()

        # Reload with bumped policy_version = "demo-v2" on the SAME database!
        policy_v2 = replace(load_policy(), version="demo-v2")
        svc2, app2 = make_env(db_path=db_file, policy=policy_v2, model_config_path=model_config)
        try:
            u1_v2 = login_client(app2, "customer", "U001")
            r2_v2 = login_client(app2, "reviewer", "R002")
            ask_v2 = u1_v2.post("/api/customer/messages", json={"text": "ORD001 迟到了申请补偿"})
            assert ask_v2.status_code == 200
            d_v2 = ask_v2.json()
            assert d_v2["outcome"] == "ticket_reused"
            assert d_v2["ticket"]["ticket_id"] == "T0001"
            assert d_v2["ticket"]["coupon_issued_yuan"] == 10
            # Even direct review approval attempt under demo-v2 returns deduplicated 409 without issuing again
            dup_v2 = r2_v2.post("/api/review/tickets/T0001/decision", json={"decision": "approve", "amount_yuan": 15, "note": "v2再批"})
            assert dup_v2.status_code == 409 and dup_v2.json()["deduplicated"] is True
            assert len(svc2.store.tickets()) == 1
            return {
                "ticket_id": "T0001",
                "double_click_dedup": dup_r1.json()["deduplicated"],
                "reviewer_switch_dedup": dup_r2.json()["deduplicated"],
                "handoff_switch_dedup": dup_handoff.json()["deduplicated"],
                "policy_v2_outcome": d_v2["outcome"],
                "policy_v2_approve_dedup": dup_v2.json()["deduplicated"],
                "total_tickets_in_db": len(svc2.store.tickets()),
                "final_coupon_issued_yuan": svc2.store.get("T0001")["coupon_issued_yuan"],
            }
        finally:
            svc2.store.close()


def check_hr08(model_config: str | None) -> dict:
    """HR08: Concurrent R001 (¥10) and R002 (¥15) approvals on the same pending order."""
    with tempfile.TemporaryDirectory(prefix="ord001-hr08-") as tmp:
        db_file = str(Path(tmp) / "hr08.sqlite3")
        svc, app = make_env(db_path=db_file, model_config_path=model_config)
        try:
            u1 = login_client(app, "customer", "U001")
            t = submit_claim_via_chat(u1, "ORD001")
            tid = t["ticket_id"]

            barrier = threading.Barrier(2)

            def fire_r1():
                barrier.wait(timeout=5)
                try:
                    res = svc.decide(tid, "R001", "approve", "客服标准10元审批", amount_yuan=None)
                    return (200, res["ticket"]["coupon_issued_yuan"], False)
                except ServiceError as exc:
                    return (exc.status, exc.extra.get("ticket", {}).get("coupon_issued_yuan"), exc.extra.get("deduplicated"))

            def fire_r2():
                barrier.wait(timeout=5)
                try:
                    res = svc.decide(tid, "R002", "approve", "主管特批15元审批", amount_yuan=15)
                    return (200, res["ticket"]["coupon_issued_yuan"], False)
                except ServiceError as exc:
                    return (exc.status, exc.extra.get("ticket", {}).get("coupon_issued_yuan"), exc.extra.get("deduplicated"))

            with ThreadPoolExecutor(max_workers=2) as pool:
                f1 = pool.submit(fire_r1)
                f2 = pool.submit(fire_r2)
                outcomes = [f1.result(), f2.result()]

            codes = sorted(x[0] for x in outcomes)
            assert codes == [200, 409], outcomes
            final_ticket = svc.store.get(tid)
            final_amt = final_ticket["coupon_issued_yuan"]
            assert final_amt in (10, 15), final_amt  # Never summed to 25!
            assert all(x[1] == final_amt for x in outcomes), outcomes
            events = svc.store.events(tid)
            assert [e["action"] for e in events].count("approved") == 1
            return {
                "concurrent_http_codes": codes,
                "single_final_amount_yuan": final_amt,
                "approved_event_count": [e["action"] for e in events].count("approved"),
                "outcomes": outcomes,
            }
        finally:
            svc.store.close()


def check_hr09(model_config: str | None) -> dict:
    """HR09: Independent multi-order handling for same customer (ORD001 & ORD005) + Mode B guard parity."""
    svc, app = make_env(model_config_path=model_config)
    try:
        u1 = login_client(app, "customer", "U001")
        r1 = login_client(app, "reviewer", "R001")
        r2 = login_client(app, "reviewer", "R002")

        t1 = submit_claim_via_chat(u1, "ORD001")
        t2 = submit_claim_via_chat(u1, "ORD005")
        assert t1["ticket_id"] != t2["ticket_id"]

        ok1 = r1.post(f"/api/review/tickets/{t1['ticket_id']}/decision", json={"decision": "approve", "note": "ORD001标准10元"})
        ok2 = r2.post(
            f"/api/review/tickets/{t2['ticket_id']}/decision",
            json={"decision": "approve", "amount_yuan": 12, "note": "ORD005主管核准12元"},
        )
        assert ok1.status_code == 200 and ok1.json()["ticket"]["coupon_issued_yuan"] == 10
        assert ok2.status_code == 200 and ok2.json()["ticket"]["coupon_issued_yuan"] == 12

        # Repeat request on ORD001 does NOT issue again and does NOT touch ORD005
        rep = u1.post("/api/customer/messages", json={"text": "ORD001 再申请一次"})
        assert rep.status_code == 200 and rep.json()["outcome"] == "ticket_reused"
        assert svc.store.get(t1["ticket_id"])["coupon_issued_yuan"] == 10
        assert svc.store.get(t2["ticket_id"])["coupon_issued_yuan"] == 12

        # Verify Mode B also enforces existing-ticket reuse on compensated order while allowing independent uncompensated order
        svc_b = DemoService(
            db_path=":memory:",
            agent_mode="B",
            model=DeterministicModeBTestAdapter(forced_amount=10, force_eligible=True),
        )
        try:
            b1 = svc_b.send_message("tb1", "U001", "ORD001 申请补偿")
            assert b1["outcome"] == "awaiting_confirmation"
            b1_c = svc_b.confirm("tb1", "U001", "confirm")
            svc_b.decide(b1_c["ticket"]["ticket_id"], "R001", "approve", "B模式审批ORD001")

            # Mode B tries to propose confirm again on ORD001 -> intercepted & reused!
            b1_dup = svc_b.send_message("tb2", "U001", "ORD001 再赔一次")
            assert b1_dup["outcome"] == "ticket_reused"
            assert b1_dup["safety_intercept"] == "existing_ticket_reuse_enforced"

            # Meanwhile ORD008 on Mode B remains independent and works cleanly!
            b8 = svc_b.send_message("tb2", "U001", "ORD008 申请补偿")
            assert b8["outcome"] == "awaiting_confirmation"
        finally:
            svc_b.store.close()

        return {
            "ord001_ticket": {"ticket_id": t1["ticket_id"], "coupon_issued_yuan": 10},
            "ord005_ticket": {"ticket_id": t2["ticket_id"], "coupon_issued_yuan": 12},
            "repeat_ord001_outcome": rep.json()["outcome"],
            "mode_b_dup_intercept": "existing_ticket_reuse_enforced",
            "mode_b_other_order_independent": True,
        }
    finally:
        svc.store.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-config", help="Optional live model JSON config path")
    parser.add_argument("--label", default="developer_self_check", help="developer_self_check or acceptance_retest")
    parser.add_argument("--out-json", help="Optional path to save JSON report")
    args = parser.parse_args()

    checks = [
        ("HR01", "有理由重审（可核实新信息 / 原处理错误，沿原工单恢复待审并保留历史）", check_hr01),
        ("HR02", "无理由／空原因拦截（仅不满意不自动重开，空原因与非法类型拒绝）", check_hr02),
        ("HR03", "状态与已发限制（非已驳回禁重审，已发券禁重审／改额／补差价）", check_hr03),
        ("HR04", "角色权限（仅R002可改额，R001标准10元，R003只读，顾客／AI禁改额）", check_hr04),
        ("HR05", "金额范围与原因（1-20整数元且非10必填说明，0/21/1.5拒绝不静默截断）", check_hr05),
        ("HR06", "可信实付上限（隔离8元单拒10与9、准主管8元；实付缺失拒发）", check_hr06),
        ("HR07", "重复与换会话／换客服／换规则版本去重（同单唯一成功补偿）", check_hr07),
        ("HR08", "并发同时批准（R001 10元 vs R002 15元原子互斥，不叠加）", check_hr08),
        ("HR09", "同一顾客不同订单独立处理及 B/C 共享执行保护一致", check_hr09),
    ]

    results = []
    failed = 0
    for code, title, fn in checks:
        try:
            evidence = fn(args.model_config)
            results.append({"group": code, "title": title, "status": "passed", "evidence": evidence})
        except Exception as exc:
            failed += 1
            results.append({"group": code, "title": title, "status": "failed", "error": f"{type(exc).__name__}: {exc}"})

    report = {
        "checked_at": now_text(),
        "run_category": args.label,
        "policy_combination": "demo-v1 + human-review-v1",
        "model_mode": "live" if args.model_config else "scripted_plus_mode_b_adapter",
        "summary": {"total_groups": len(checks), "passed": len(checks) - failed, "failed": failed},
        "results": results,
    }
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out_json:
        Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out_json).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
