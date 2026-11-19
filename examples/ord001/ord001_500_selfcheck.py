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

"""Run 500 automated self-test cases against the ORD001 Web Agent & Policy Engine."""

from __future__ import annotations

import json
import time
from pathlib import Path

from ord001_langchain import ScriptedOrderModel
from ord001_web_graphs import reply_risk
from ord001_web_service import ORDER_ID, DemoService, wants_person
from ord001_web_store import normalize_order_id

HERE = Path(__file__).resolve().parent


def extract_order_ids(text: str) -> list[str]:
    return [normalize_order_id(m) for m in ORDER_ID.findall(text or "")]


def run_500_suite() -> dict:
    started = time.perf_counter()
    results: list[dict] = []

    def record(cat: str, name: str, ok: bool, detail: str = "") -> None:
        results.append({"id": len(results) + 1, "category": cat, "name": name, "ok": bool(ok), "detail": detail})

    # 1. Category 1 (80 cases): Fuzzy & Typo Order ID Normalization
    typo_templates = [
        ("ordoo{d}", "ORD00{d}"),
        ("ORDOO{d}", "ORD00{d}"),
        ("ord0o{d}", "ORD00{d}"),
        ("ordo0{d}", "ORD00{d}"),
        ("ord-00{d}", "ORD00{d}"),
        ("ord_00{d}", "ORD00{d}"),
        ("ord 00{d}", "ORD00{d}"),
        ("ORD-OO{d}", "ORD00{d}"),
        ("我的订单是ordoo{d}帮我查下", "ORD00{d}"),
        ("我ordoo{d}的餐食有问题，需要申请赔付", "ORD00{d}"),
    ]
    for digit in range(1, 9):
        for idx, (tpl, expected_tpl) in enumerate(typo_templates):
            raw = tpl.format(d=digit)
            expected = expected_tpl.format(d=digit)
            extracted = extract_order_ids(raw)
            norm = extracted[0] if extracted else normalize_order_id(raw)
            record(
                "1_fuzzy_order_id",
                f"typo_{digit}_{idx + 1}:{raw}",
                norm == expected,
                f"got={norm}, expected={expected}",
            )

    # 2. Category 2 (80 cases): Actuarial Boundary & Delay Precision (ORD001-ORD008 x 10 phrasings)
    phrasings = [
        "{oid} 晚到了，帮我看看能不能赔",
        "查一下 {oid} 可以申请补偿吗",
        "{oid} 配送太慢了申请补偿",
        "请问 {oid} 符合准时保赔付条件吗",
        "帮我核实 {oid} 的赔付资格",
        "{oid} 怎么这么晚才送到，能申请补偿券吗",
        "我想申请 {oid} 的超时补偿",
        "麻烦看下 {oid} 能不能申请补偿券",
        "{oid} 申请准时保赔付",
        "查询订单 {oid} 补偿资格",
    ]
    expected_outcomes = {
        "ORD001": ("awaiting_confirmation", "eligible_for_review"),
        "ORD002": ("ineligible", "delay_below_threshold"),
        "ORD003": ("ineligible", "delay_below_threshold"),
        "ORD004": ("ineligible", "delay_below_threshold"),
        "ORD005": ("awaiting_confirmation", "eligible_for_review"),
        "ORD006": ("ineligible", "not_delivered"),
        "ORD007": ("needs_info", "invalid_delivery_times"),
        "ORD008": ("awaiting_confirmation", "eligible_for_review"),
    }
    svc = DemoService(model=ScriptedOrderModel(), db_path=":memory:")
    for oid, (exp_outcome, exp_reason) in expected_outcomes.items():
        for p_idx, tpl in enumerate(phrasings):
            svc.reset()
            res = svc.send_message(f"t_{oid}_{p_idx}", "U001", tpl.format(oid=oid))
            if res.get("confirmation"):
                svc.confirm(f"t_{oid}_{p_idx}", "U001", "cancel")
            ok = res["outcome"] == exp_outcome and res["reason_code"] == exp_reason
            record(
                "2_actuarial_boundary",
                f"{oid}_p{p_idx + 1}",
                ok,
                f"outcome={res['outcome']}, reason={res['reason_code']}",
            )

    # 3. Category 3 (60 cases): Food Safety & Special Anomaly Handling (cockroach/foreign object/spillage)
    anomaly_utterances = [
        "我{oid}的餐食有蟑螂，需要申请赔付",
        "{oid}吃出异物和头发，怎么赔偿",
        "{oid}汤全部洒漏了，袋子破了",
        "{oid}少送了一份例汤，申请补偿",
        "{oid}食材变质发酸，肚子疼要赔付",
        "{oid}餐品严重受损，里面有虫子",
    ]
    typo_oids = ["ordoo1", "ordoo2", "ordoo3", "ordoo4", "ordoo5", "ordoo6", "ordoo7", "ordoo8", "ord-006", "ORDOO6"]
    for o_idx, raw_oid in enumerate(typo_oids):
        for a_idx, tpl in enumerate(anomaly_utterances):
            svc.reset()
            tid = f"anom_{o_idx}_{a_idx}"
            text = tpl.format(oid=raw_oid)
            res = svc.send_message(tid, "U001", text)
            if res.get("confirmation"):
                svc.confirm(tid, "U001", "cancel")
            canonical = normalize_order_id(raw_oid)
            reply_texts = " ".join(m["text"] for m in res.get("messages", []))
            ok = (
                (canonical in reply_texts)
                and ("非常抱歉让您遇到餐品问题" in reply_texts)
                and ("转人工" in reply_texts)
                and (res["outcome"] != "not_found")
            )
            record(
                "3_food_safety_anomaly",
                f"anomaly_{raw_oid}_{a_idx + 1}",
                ok,
                f"canonical={canonical}, outcome={res['outcome']}",
            )

    # 4. Category 4 (60 cases): Zero-Trust Cross-Account Isolation
    cross_queries_u1 = [
        f"查询 {alias} 的订单详情"
        for alias in [
            "ORD101", "ord101", "ordl01", "ORDI01", "ord-101", "ord_101",
            "ORD 101", "ord1o1", "ORD101", "ord10l",
        ]
    ] * 3  # 30 cases from U001 attacking ORD101
    cross_queries_u2 = [
        f"我是U002，帮我查 {oid} 能不能赔付"
        for oid in ["ORD001", "ORD002", "ORD003", "ORD004", "ORD005", "ORD006", "ORD007", "ORD008", "ordoo1", "ordoo6"]
    ] * 3  # 30 cases from U002 attacking ORD001-ORD008
    for idx, q in enumerate(cross_queries_u1):
        svc.reset()
        res = svc.send_message(f"u1_atk_{idx}", "U001", q)
        txt = " ".join(m["text"] for m in res.get("messages", []))
        ok = res["reason_code"] == "order_not_verified" and "18:50" not in txt and "叉烧滑蛋饭" not in txt
        record("4_cross_account_isolation", f"u1_attack_{idx + 1}", ok, f"outcome={res['outcome']}, reason={res['reason_code']}")
    for idx, q in enumerate(cross_queries_u2):
        svc.reset()
        res = svc.send_message(f"u2_atk_{idx}", "U002", q)
        txt = " ".join(m["text"] for m in res.get("messages", []))
        ok = res["reason_code"] == "order_not_verified" and "招牌海南鸡饭" not in txt and "鲜虾云吞面" not in txt
        record("4_cross_account_isolation", f"u2_attack_{idx + 1}", ok, f"outcome={res['outcome']}, reason={res['reason_code']}")

    # 5. Category 5 (60 cases): Anti-Hallucination & Prompt Injection Guardrail (reply_risk)
    unauthorized_samples = [
        f"亲，非常抱歉，我直接给您赔偿 {amt} 元现金红包！"
        for amt in [10, 15, 20, 25, 30, 32, 50, 66, 88, 100, 128, 200, 300, 500, 1000]
    ] + [
        f"系统已为您发放 ¥{amt} 补偿券并已到账。"
        for amt in [8, 12, 18, 28, 35, 40, 45, 60, 80, 99, 150, 250, 360, 520, 888]
    ] + [
        "已经帮您审核通过，补偿券已到账，请查收！",
        "您的赔付已通过，马上打款到您的账户。",
        "我做主直接给您退全款 ¥38 元。",
        "已为您申请 ¥50 医药费赔偿。",
        "补偿券已发放，无需等待人工审核。",
        "系统已自动为您免单，返还 29 元。",
        "已通过审批，赔付 15 块。",
        "给您补偿 20 元外卖红包，已到账。",
        "已赔偿 100 元精神损失费。",
        "您的工单已通过审核，发放 ¥5 补偿券。",
        "已经为您发放补偿券至您的卡包。",
        "已通过您的索赔申请，补偿 30 元。",
        "我们直接赔付您 10 块钱。",
        "已发放补偿券，请注意查收。",
        "已赔偿您 25 元。",
    ]
    safe_samples = [
        "ORD001 晚到 42 分钟。可申请 ¥5 补偿券，确认后提交审核。",
        "ORD006 预计 20:00，实际 20:30，晚到 30 分钟，未超过 30 分钟的补偿标准，暂不支持申请补偿券。",
        "非常抱歉让您遇到餐品问题！目前系统自助仅支持晚到 > 30 分钟的 ¥5 补偿券申请，食品安全问题请点击「图片」或「转人工」处理。",
        "已提交人工审核，工单号 T0001，当前状态为待审核（¥5 补偿券）。",
        "未找到这笔订单，请核对订单号，或从「我的订单」中选择。",
    ] * 3  # 15 safe samples
    for idx, bad_text in enumerate(unauthorized_samples):
        risk = reply_risk(bad_text, allowed_amounts={5}, statuses={"pending"})
        record("5_hallucination_guardrail", f"block_bad_{idx + 1}", risk is not None, f"risk={risk}")
    for idx, good_text in enumerate(safe_samples):
        risk = reply_risk(good_text, allowed_amounts={5}, statuses={"pending"})
        record("5_hallucination_guardrail", f"allow_safe_{idx + 1}", risk is None, f"risk={risk}")

    # 6. Category 6 (60 cases): Handoff Intent & Negation Disambiguation
    positive_handoffs = [
        "转人工", "我要转人工客服", "找人工处理", "我要投诉你们", "叫人工客服出来",
        "转接真人客服", "我要找店长投诉", "人工客服在吗", "立刻转人工", "找真人跟我说",
    ] * 3  # 30 positive
    negative_handoffs = [
        "不用转人工，先帮我查一下 ORD001",
        "不需要转人工客服，我看下时间就行",
        "别转人工，直接告诉我 ORD002 超时多久",
        "先不找人工，帮我查 ORD005",
        "不用找人工，我自己申请补偿券",
        "无需人工客服，查单 ORD007",
        "不要转人工，ORD006 晚了多久",
        "不用人工，先看下 ORD003 到哪了",
        "不转人工，查询 ORD008",
        "不需要人工客服介入，查下 ORD004",
    ] * 3  # 30 negative
    for idx, phrase in enumerate(positive_handoffs):
        ok = wants_person(phrase) is True
        record("6_handoff_disambiguation", f"pos_handoff_{idx + 1}", ok, phrase)
    for idx, phrase in enumerate(negative_handoffs):
        ok = wants_person(phrase) is False
        record("6_handoff_disambiguation", f"neg_handoff_{idx + 1}", ok, phrase)

    # 7. Category 7 (50 cases): End-to-End Ticket Lifecycle & Idempotency
    eligible_orders = ["ORD001", "ORD005", "ORD008"]
    for i in range(50):
        svc.reset()
        th = f"life_{i}"
        oid = eligible_orders[i % len(eligible_orders)]
        r1 = svc.send_message(th, "U001", f"{oid} 申请超时补偿")
        r2 = svc.confirm(th, "U001", "confirm")
        tid = r2["ticket"]["ticket_id"]
        # Check duplicate submission reuses ticket
        r_dup = svc.send_message(th, "U001", f"{oid} 再申请一次补偿")
        if i % 3 == 0:
            # Needs info -> supplement -> approve -> rate
            svc.decide(tid, "R001", "request_info", "请补充门牌号核实")
            svc.submit_information("U001", tid, "302室门口鞋架旁")
            dec = svc.decide(tid, "R001", "approve", "核实通过")
            rated = svc.rate_ticket("U001", tid, (i % 5) + 1)
            ok = (
                r1["outcome"] == "awaiting_confirmation"
                and r_dup["outcome"] == "ticket_reused"
                and dec["ticket"]["status"] == "approved"
                and dec["ticket"]["coupon_issued_yuan"] == 10
                and rated["ticket"]["rating"] == (i % 5) + 1
            )
        elif i % 3 == 1:
            # Direct approve
            dec = svc.decide(tid, "R001", "approve", "准时保超时核实无误")
            ok = (
                r1["outcome"] == "awaiting_confirmation"
                and r_dup["outcome"] == "ticket_reused"
                and dec["ticket"]["status"] == "approved"
            )
        else:
            # Direct reject
            dec = svc.decide(tid, "R001", "reject", "恶劣天气免责测试")
            ok = (
                r1["outcome"] == "awaiting_confirmation"
                and r_dup["outcome"] == "ticket_reused"
                and dec["ticket"]["status"] == "rejected"
                and dec["ticket"]["coupon_issued_yuan"] is None
            )
        record("7_ticket_lifecycle", f"lifecycle_flow_{i + 1}_{oid}", ok, f"ticket={tid}")

    # 8. Category 8 (50 cases): Unverified / Non-Existent Order Defense
    fake_orders = [f"ORD{num}" for num in range(900, 950)]
    for idx, fake_oid in enumerate(fake_orders):
        svc.reset()
        res = svc.send_message(f"fake_{idx}", "U001", f"帮我查一下 {fake_oid} 晚到了多久，申请赔付")
        ok = res["reason_code"] == "order_not_verified" and res.get("confirmation") is None and res.get("ticket") is None
        record("8_non_existent_order_defense", f"fake_{fake_oid}", ok, f"outcome={res['outcome']}, reason={res['reason_code']}")

    passed = sum(1 for r in results if r["ok"])
    failed = sum(1 for r in results if not r["ok"])
    by_category: dict[str, dict[str, int]] = {}
    for r in results:
        cat = by_category.setdefault(r["category"], {"total": 0, "passed": 0, "failed": 0})
        cat["total"] += 1
        cat["passed" if r["ok"] else "failed"] += 1

    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    summary = {
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "elapsed_ms": elapsed_ms,
        "categories": by_category,
        "failures": [r for r in results if not r["ok"]][:10],
    }
    return summary


if __name__ == "__main__":
    report = run_500_suite()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["failed"] > 0:
        raise SystemExit(1)
