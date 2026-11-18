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

"""Re-run P01–P03 on the ORD001 web demo plus the Studio reference graph, and print what actually happened.

Each case gets a fresh in-process server with the scripted model. With --base-url the cases drive a
running server instead and clear its demo data before each case.
"""

import argparse
import asyncio
import json
import os
import platform
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from starlette.testclient import TestClient

from ord001_compensation import build_compensation_graph
from ord001_langchain import ScriptedOrderModel
from ord001_web import create_app
from ord001_web_service import DemoService
from ord001_web_store import DECISION_STATUS, STATUS_TEXT
from ord001_web_texts import NOT_VERIFIED, delay_text

CLAIM = "我的外卖 ORD001 迟到了，可以申请补偿吗？"
NO_ORDER = "我的外卖迟到了，可以申请补偿吗？"
# Facts of U002's ORD101 that must never reach U001.
LEAKS = ("18:00", "18:50", "50 分钟", "U002", "模拟餐厅", "67餐厅")
PACKAGES = ("langgraph", "langchain", "langchain-core", "langchain-openai", "starlette", "uvicorn", "httpx")
DEMO_V1 = {"version": "demo-v1", "threshold_minutes": 30, "include_threshold": False, "coupon_yuan": 10}
LABEL = {"approve": "批准", "reject": "驳回"}
TICKET_KEYS = ("ticket_id", "order_id", "status", "late_seconds", "policy_version", "proposed_coupon_yuan",
               "coupon_issued_yuan", "review_note")
RUN_KEYS = ("event", "customer_id", "order_id", "outcome", "reason_code", "ticket_id", "policy_version", "model",
            "latency_ms")


def call(client, path, body=None, **kwargs):
    """GET without a body, POST JSON with one. Returns the status and the parsed body."""
    response = client.get(path, **kwargs) if body is None else client.post(path, json=body, **kwargs)
    try:
        return response.status_code, response.json()
    except ValueError:
        return response.status_code, None


class Case:
    def __init__(self, name: str, expected: str, *, record_only: bool = False):
        self.name, self.expected, self.record_only = name, expected, record_only
        self.actual, self.failures, self.evidence = "", [], {}

    def check(self, ok, failure: str) -> bool:
        if not ok:
            self.failures.append(failure)
        return bool(ok)

    def verdict(self) -> str:
        if self.record_only:
            return "仅记录"
        return "通过" if not self.failures else "未通过：" + "；".join(self.failures)

    def as_dict(self) -> dict:
        return {"name": self.name, "expected": self.expected, "actual": self.actual,
                "verdict": self.verdict(), "failures": self.failures, "evidence": self.evidence}


class Server:
    """Clients for one demo server: a fresh in-process app per case, or the live server after a reset."""

    def __init__(self, base_url: str | None):
        self.base_url, self.app, self.clients = base_url, None, []

    def fresh(self) -> None:
        self.close()
        if not self.base_url:
            self.app = create_app(DemoService(model=ScriptedOrderModel()))
            return
        status, body = call(self.client("reviewer", "R001"), "/api/review/reset", {})
        if status != 200:
            raise RuntimeError(f"重置演示数据失败：HTTP {status} {body}")

    def client(self, role: str | None = None, person_id: str | None = None):
        client = httpx.Client(base_url=self.base_url, timeout=120) if self.base_url else TestClient(self.app)
        self.clients.append(client)
        if role:
            key = f"{role}_id"
            path = "/api/customer/login" if role == "customer" else "/api/review/login"
            status, body = call(client, path, {key: person_id})
            if status != 200:
                raise RuntimeError(f"{person_id} 登录失败：HTTP {status} {body}")
        return client

    def close(self) -> None:
        for client in self.clients:
            client.close()
        self.clients.clear()


def run(case: Case, step, *args) -> Case:
    try:
        step(case, *args)
    except Exception as exc:  # one broken step should not hide the remaining cases
        case.failures.append(f"运行出错 {type(exc).__name__}: {exc}")
        case.actual = case.actual or f"{type(exc).__name__}: {exc}"
    return case


def expect_ok(case: Case, client, path: str, body=None, **kwargs) -> dict:
    status, data = call(client, path, body, **kwargs)
    case.check(status == 200, f"{path} 返回 HTTP {status}：{data}")
    return data if isinstance(data, dict) else {}


def replies(turn: dict) -> str:
    return " ".join(item["text"] for item in turn.get("messages", []) if item.get("role") == "assistant")


def brief(turn: dict) -> dict:
    """What a tester compares for one customer turn."""
    ticket = turn.get("ticket")
    return {
        "outcome": turn.get("outcome"),
        "reason_code": turn.get("reason_code"),
        "confirmation": turn.get("confirmation"),
        "ticket": {key: ticket.get(key) for key in TICKET_KEYS} if ticket else None,
        "reply": replies(turn),
    }


def say(case: Case, client, text: str) -> dict:
    turn = expect_ok(case, client, "/api/customer/messages", {"text": text})
    case.evidence.setdefault("对话", []).append({"顾客": text, **brief(turn)})
    return turn


def answer(case: Case, client, value: str) -> dict:
    turn = expect_ok(case, client, "/api/customer/confirm", {"answer": value})
    case.evidence.setdefault("对话", []).append({"顾客": f"[{value}]", **brief(turn)})
    return turn


def ask(case: Case, client, order_id: str) -> dict:
    return say(case, client, f"我的外卖 {order_id} 迟到了，可以申请补偿吗？")


def my_tickets(case: Case, client) -> list:
    return expect_ok(case, client, "/api/customer/tickets").get("tickets", [])


def queue(case: Case, client) -> tuple[list, list]:
    data = expect_ok(case, client, "/api/review/tickets")
    return data.get("pending", []), data.get("decided", [])


def no_ticket(case: Case, customer, reviewer) -> bool:
    pending, decided = queue(case, reviewer)
    return not my_tickets(case, customer) and not pending and not decided


def logged_outcomes(case: Case, reviewer) -> list:
    """Outcomes in the server's run log, without the reset entry a live server writes."""
    runs = expect_ok(case, reviewer, "/api/review/runs").get("runs", [])
    case.evidence["运行记录"] = [{key: run.get(key) for key in RUN_KEYS} for run in runs if run.get("event") != "reset"]
    return [run["outcome"] for run in case.evidence["运行记录"]]


def signed_in(server: Server) -> tuple:
    """A fresh server with U001 and R001 signed in."""
    server.fresh()
    return server.client("customer", "U001"), server.client("reviewer", "R001")


def check_policy(case: Case, server: Server) -> None:
    server.fresh()
    health = expect_ok(case, server.client(), "/api/health")
    case.evidence = {key: health.get(key) for key in ("policy", "data_version", "service_date", "model")}
    case.check(health.get("policy") == DEMO_V1, f"服务端规则为 {health.get('policy')}")
    case.actual = (f"{json.dumps(health.get('policy'), ensure_ascii=False)}；订单数据 {health.get('data_version')}；"
                   f"模型 {health.get('model')}")


def p01(case: Case, server: Server, decision: str) -> None:
    final, note = DECISION_STATUS[decision], f"演示：审批员{LABEL[decision]}"
    customer, reviewer = signed_in(server)

    turn = say(case, customer, CLAIM)
    claim = turn.get("confirmation") or {}
    case.check(turn.get("outcome") == "awaiting_confirmation", f"咨询后为 {turn.get('outcome')}")
    case.check((claim.get("late_seconds"), claim.get("policy_version"), claim.get("proposed_coupon_yuan"))
               == (3000, "demo-v1", 10), f"确认框内容为 {claim}")
    case.check(no_ticket(case, customer, reviewer), "顾客确认前已有工单")

    done = answer(case, customer, "confirm")
    ticket = done.get("ticket") or {}
    tid = ticket.get("ticket_id")
    case.check(done.get("outcome") == "ticket_created" and ticket.get("status") == "pending",
               f"确认后为 {done.get('outcome')} / {ticket.get('status')}")
    case.check(ticket.get("coupon_issued_yuan") is None, "审批前已记录发券")
    said = replies(turn) + replies(done)
    case.check("已发放" not in said and "已批准" not in said, "审批前的回复出现了「已发放」或「已批准」")
    twice = call(customer, "/api/customer/confirm", {"answer": "confirm"})[0]
    case.check(twice == 409, f"重复点「确认提交」返回 HTTP {twice}")

    pending, decided = queue(case, reviewer)
    case.evidence["审批端待审"] = [{**{key: item.get(key) for key in TICKET_KEYS},
                                "审批节点已暂停": bool(item.get("review_request"))} for item in pending]
    case.check([item["ticket_id"] for item in pending] == [tid] and pending[0].get("review_request"),
               "审批端没有同一张待审工单，或审批节点没有暂停")
    case.check(not decided, "审批前已有处理记录")

    again = say(case, customer, CLAIM)
    case.check(again.get("outcome") == "ticket_reused" and (again.get("ticket") or {}).get("ticket_id") == tid,
               f"重试结果为 {again.get('outcome')}")
    case.check(len(my_tickets(case, customer)) == 1, "重试后工单不止一张")

    # Only a signed-in reviewer may decide, and only the owner may open the ticket.
    path = f"/api/review/tickets/{tid}/decision"
    refused = {
        "顾客账号提交审批": call(customer, path, {"decision": decision})[0],
        "未登录提交审批": call(server.client(), path, {"decision": decision})[0],
        "跨站提交审批": call(reviewer, path, {"decision": decision}, headers={"Origin": "http://evil.example"})[0],
        "不支持的审批动作 invalid_action": call(reviewer, path, {"decision": "invalid_action"})[0],
        "U002 打开这张工单": call(server.client("customer", "U002"), f"/api/customer/tickets/{tid}")[0],
    }
    case.evidence["越权与无效请求的 HTTP 状态"] = refused
    case.check(list(refused.values()) == [401, 401, 403, 400, 404], f"越权或无效请求返回 {refused}")

    result = expect_ok(case, reviewer, path, {"decision": decision, "note": note}).get("ticket") or {}
    case.check(result.get("status") == final, f"审批后为 {result.get('status')}")
    repeat = call(reviewer, path, {"decision": decision})[0]
    case.check(repeat == 409, f"重复审批返回 HTTP {repeat}")

    view = expect_ok(case, customer, f"/api/customer/tickets/{tid}")
    seen = view.get("ticket") or {}
    actions = [item["action"] for item in view.get("timeline", [])]
    case.evidence["顾客端同一工单"] = {**{key: seen.get(key) for key in TICKET_KEYS}, "timeline": actions}
    coupon = 10 if decision == "approve" else None
    case.check((seen.get("status"), seen.get("late_seconds"), seen.get("coupon_issued_yuan"), seen.get("review_note"))
               == (final, 3000, coupon, note), f"顾客端工单为 {seen}")
    case.check(actions == ["submitted", final], f"工单记录为 {actions}")
    case.check("reviewer_id" not in seen, "顾客端看到了审批员编号")

    after = say(case, customer, CLAIM)
    case.check(after.get("outcome") == "ticket_reused" and STATUS_TEXT[final] in replies(after),
               "审批后再问，回复与工单状态不一致")
    count = len(my_tickets(case, customer))
    case.check(count == 1, f"审批后有 {count} 张工单")
    logged = logged_outcomes(case, reviewer)
    case.check(logged == ["awaiting_confirmation", "ticket_created", "ticket_reused", final, "ticket_reused"],
               f"运行记录为 {logged}")
    case.actual = (f"工单 {tid}：确认前无工单；确认后 {ticket.get('status')}、券 {ticket.get('coupon_issued_yuan')}；"
                   f"重复确认 HTTP {twice}，重试为 {again.get('outcome')}；越权与无效请求 {list(refused.values())}；"
                   f"{decision} 后顾客端同一工单为 {seen.get('status')}、券 {seen.get('coupon_issued_yuan')}、"
                   f"记录 {'→'.join(actions)}；再问回复「{replies(after)}」；共 {count} 张工单")


def refused_orders(case: Case, server: Server, orders) -> None:
    """Orders that cannot be submitted: an explanation, no confirmation box and no ticket."""
    customer, reviewer = signed_in(server)
    seen = []
    for order_id, outcome, reason, late in orders:
        turn = ask(case, customer, order_id)
        got = (turn.get("outcome"), turn.get("reason_code"))
        seen.append(f"{order_id} {got[0]} / {got[1]}，回复「{replies(turn)}」")
        case.check(got == (outcome, reason) and not turn.get("confirmation"), f"{order_id} 为 {got[0]} / {got[1]}")
        if late is not None:
            case.check(delay_text(late) in replies(turn), f"{order_id} 的回复里没有「{delay_text(late)}」")
    clean = no_ticket(case, customer, reviewer)
    case.check(clean, "出现了工单")
    case.actual = "；".join(seen) + ("；无确认框、无工单" if clean else "；出现了工单")


def boundary_reject(case: Case, server: Server) -> None:
    customer, reviewer = signed_in(server)
    turn = ask(case, customer, "ORD005")
    late = (turn.get("confirmation") or {}).get("late_seconds")
    case.check((turn.get("outcome"), turn.get("reason_code"), late)
               == ("awaiting_confirmation", "eligible_for_review", 1801),
               f"咨询后为 {turn.get('outcome')} / {turn.get('reason_code')}，{late} 秒")
    tid = (answer(case, customer, "confirm").get("ticket") or {}).get("ticket_id")
    expect_ok(case, reviewer, f"/api/review/tickets/{tid}/decision", {"decision": "reject"})
    seen = expect_ok(case, customer, f"/api/customer/tickets/{tid}").get("ticket") or {}
    case.evidence["顾客端同一工单"] = {key: seen.get(key) for key in TICKET_KEYS}
    case.check((seen.get("status"), seen.get("late_seconds"), seen.get("policy_version"))
               == ("rejected", 1801, "demo-v1"), f"驳回后工单为 {seen}")
    case.actual = (f"{late} 秒，{turn.get('outcome')} / {turn.get('reason_code')}；确认后工单 {tid} 待审；"
                   f"reject 后同一工单为 {seen.get('status')}，仍为 {seen.get('late_seconds')} 秒")


def cancel_31(case: Case, server: Server) -> None:
    customer, reviewer = signed_in(server)
    turn = ask(case, customer, "ORD008")
    late = (turn.get("confirmation") or {}).get("late_seconds")
    case.check(turn.get("outcome") == "awaiting_confirmation" and late == 1860,
               f"咨询后为 {turn.get('outcome')}，{late} 秒")
    blocked = call(customer, "/api/customer/messages", {"text": CLAIM})[0]
    case.check(blocked == 409, f"确认框未处理时再发消息返回 HTTP {blocked}")
    done = answer(case, customer, "cancel")
    clean = no_ticket(case, customer, reviewer)
    case.check(done.get("outcome") == "claim_cancelled" and clean, f"暂不提交后为 {done.get('outcome')}")
    again = ask(case, customer, "ORD008")
    case.check(again.get("outcome") == "awaiting_confirmation", f"再次咨询为 {again.get('outcome')}")
    case.actual = (f"{late} 秒，{turn.get('outcome')}；确认框未处理时再发消息 HTTP {blocked}；暂不提交 → "
                   f"{done.get('outcome')}，{'无工单' if clean else '出现了工单'}；再问为 {again.get('outcome')}")


def p03_other(case: Case, server: Server) -> None:
    customer, reviewer = signed_in(server)
    first = say(case, customer, NO_ORDER)
    case.check(first.get("outcome") == "not_selected" and "订单号" in replies(first),
               f"未给订单号时为 {first.get('outcome')}")
    second = say(case, customer, "订单号是 ORD101")
    got = (second.get("outcome"), second.get("reason_code"))
    case.check(got == ("unauthorized", "order_not_verified") and NOT_VERIFIED in replies(second),
               f"他人订单为 {got[0]} / {got[1]}")
    shown = json.dumps([second, expect_ok(case, customer, "/api/customer/state")], ensure_ascii=False)
    leaked = [word for word in LEAKS if word in shown]
    case.check(not leaked, f"顾客端拿到了他人订单的信息：{leaked}")
    orders = [order["order_id"] for order in expect_ok(case, customer, "/api/customer/orders").get("orders", [])]
    case.check("ORD101" not in orders, "U001 的订单列表里有 ORD101")
    clean = no_ticket(case, customer, reviewer)
    case.check(clean, "出现了工单")
    logged = logged_outcomes(case, reviewer)
    case.check(logged == ["not_selected", "unauthorized"], f"运行记录为 {logged}")
    owner = expect_ok(case, server.client("customer", "U002"), "/api/customer/messages",
                      {"text": "我的外卖 ORD101 迟到了，可以申请补偿吗？"})
    case.evidence["对照：U002 本人查询 ORD101"] = brief(owner)
    case.check(owner.get("outcome") == "awaiting_confirmation", f"对照组 U002 本人查 ORD101 为 {owner.get('outcome')}")
    case.actual = (f"先追问「{replies(first)}」；ORD101 → {got[0]} / {got[1]}，回复「{replies(second)}」；"
                   f"{'未出现他人订单信息' if not leaked else '出现了 ' + '、'.join(leaked)}；"
                   f"{'无工单' if clean else '出现了工单'}；日志 {logged}；对照组 U002 本人为 {owner.get('outcome')}")


def p03_missing(case: Case, server: Server) -> None:
    customer, reviewer = signed_in(server)
    turn = ask(case, customer, "ORD999")
    got = (turn.get("outcome"), turn.get("reason_code"))
    case.check(got == ("not_found", "order_not_verified") and NOT_VERIFIED in replies(turn),
               f"查无记录为 {got[0]} / {got[1]}")
    clean = no_ticket(case, customer, reviewer)
    case.check(clean, "出现了工单")
    logged = logged_outcomes(case, reviewer)
    case.check(logged == ["not_found"], f"运行记录为 {logged}")
    case.actual = (f"{got[0]} / {got[1]}，回复「{replies(turn)}」，与未授权是同一句；"
                   f"{'无工单' if clean else '出现了工单'}；日志 {logged}")

async def studio_reference(case: Case) -> None:
    """Keep the published reference graph runnable; web-specific checks use the new graph above."""
    previous = os.environ.get("ORD001_DELIVERED_AT")
    records = []
    try:
        for delivered, decision in (("18:50", "approve"), ("18:50", "reject"), ("18:30", None), ("18:31", "reject")):
            os.environ["ORD001_DELIVERED_AT"] = delivered
            graph = build_compensation_graph(ScriptedOrderModel(), InMemorySaver())
            config = {"configurable": {"thread_id": f"reference-{delivered}-{decision}"}}
            paused = await graph.ainvoke({"messages": [{"role": "user", "content": CLAIM}]}, config)
            case.check(paused.get("late_minutes") == int(delivered[-2:]), f"参考图的延误为 {paused.get('late_minutes')}")
            if decision:
                case.check(paused.get("status") == "pending" and bool(paused.get("__interrupt__")),
                           f"参考图 {delivered} 没有暂停待审")
                final = await graph.ainvoke(Command(resume=decision), config)
                case.check(final.get("status") == DECISION_STATUS[decision], f"参考图审批后为 {final.get('status')}")
            else:
                final = paused
                case.check(final.get("status") == "ineligible" and not final.get("__interrupt__"),
                           "参考图恰好 30 分钟没有直接结束")
            records.append({"delivered_at": delivered, "decision": decision, "before": paused.get("status"),
                            "after": final.get("status"), "late_minutes": final.get("late_minutes")})
    finally:
        if previous is None:
            os.environ.pop("ORD001_DELIVERED_AT", None)
        else:
            os.environ["ORD001_DELIVERED_AT"] = previous
    case.evidence["Studio 参考图"] = records
    case.actual = "；".join(f"{r['delivered_at']} {r['before']} → {r['after']}" for r in records)


def package_versions() -> dict:
    result = {}
    for package in PACKAGES:
        try:
            result[package] = version(package)
        except PackageNotFoundError:
            result[package] = "not installed"
    return result


def markdown_report(report: dict) -> str:
    summary = report["summary"]
    lines = ["# ORD001 网页开发验收记录", "", f"运行时间：{report['checked_at']}。状态：待组员复核。",
             f"模式：{report['mode']}。通过 {summary['passed']} 项，失败 {summary['failed']} 项，范围说明 {summary['record_only']} 项。", "",
             "本次使用模拟模型、模拟订单和 demo-v1；不代表正式模型评测或正式政策验收。", "",
             "| 用例 | 预期 | 实际 | 结果 |", "|---|---|---|---|"]
    def cell(value):
        return str(value).replace("|", "\\|").replace("\n", " ")
    for case in report["cases"]:
        lines.append("| " + " | ".join(cell(case[key]) for key in ("name", "expected", "actual", "verdict")) + " |")
    lines.extend(["", "## 运行环境", "", f"Python {report['environment']['python']}；{report['environment']['platform']}。", ""])
    lines.extend(f"- {name}: {value}" for name, value in report["environment"]["packages"].items())
    lines.extend(["", "完整请求、工单与运行记录保存在同次运行的 JSON 文件中。", ""])
    return "\n".join(lines)


def save_report(path: str, text: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", help="本机运行中的服务；逐项清空模拟工单和对话，请勿与手动演示同时使用")
    parser.add_argument("--json", dest="json_path", help="完整验收证据的 JSON 文件路径")
    parser.add_argument("--markdown", dest="markdown_path", help="便于组员阅读的 Markdown 文件路径")
    args = parser.parse_args()
    if args.base_url:
        parsed = urlsplit(args.base_url)
        if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost") or parsed.username or parsed.password:
            parser.error("--base-url 只接受本机 http://127.0.0.1:端口 或 http://localhost:端口")
    server = Server(args.base_url)
    cases = []

    def add(name, expected, step, *values):
        case = run(Case(name, expected), step, *values)
        cases.append(case)
        print(f"{case.name}：{case.verdict()}", flush=True)

    try:
        add("配置", "demo-v1：已送达且 >30 分钟，¥10 券", check_policy, server)
        for decision in ("approve", "reject"):
            add(f"P01 {LABEL[decision]}", "顾客确认前无工单；确认后待审；人工处理后同一工单回显；重试复用", p01, server, decision)
        add("P02 晚 10／30 分钟", "两笔均不符合，无确认框、无工单", refused_orders, server,
            [("ORD002", "ineligible", "delay_below_threshold", 600),
             ("ORD003", "ineligible", "delay_below_threshold", 1800)])
        add("P02 边界 29:59", "1799 秒不符合，无工单", refused_orders, server,
            [("ORD004", "ineligible", "delay_below_threshold", 1799)])
        add("P02 边界 30:01", "1801 秒可提交，驳回后同一工单仍保留原始秒数", boundary_reject, server)
        add("P02 晚 31 分钟并取消", "可申请；取消不建单；可重新咨询", cancel_31, server)
        add("P03 缺订单号后提供他人订单", "先追问，再拒绝核验；不泄露订单事实、不建单；本人可正常查询", p03_other, server)
        add("P03 查无订单", "与未授权使用相同的顾客回复；服务端日志区分 not_found", p03_missing, server)
        add("未送达", "解释仅处理已送达订单，不建单", refused_orders, server,
            [("ORD006", "ineligible", "not_delivered", None)])
        add("送达时间缺失", "提示资料不足，不建单", refused_orders, server,
            [("ORD007", "needs_info", "invalid_delivery_times", None)])
        add("Studio 参考图", "独立验证 50 分钟批准／驳回与 30／31 分钟分流",
            lambda case: asyncio.run(studio_reference(case)))
        scope = Case("补资料扩展的独立验收", "补资料专项与新版浏览器检查分别验证恢复链路，不并入本脚本的12项", record_only=True)
        scope.actual = (
            "request_info 需填写补资料说明；工单进入 needs_info，由本人补充后同一工单回到 pending 再审。"
            "该链路的权限、多轮历史、数据库迁移与浏览器交互另由补资料专项检查和 UI 检查验证；"
            "实际结果见 evidence/2026-11-10-product/。本行仅说明验收范围，不计为本脚本通过项。"
        )
        cases.append(scope)
    finally:
        server.close()

    failed = sum(bool(case.failures) for case in cases)
    recorded = sum(case.record_only for case in cases)
    report = {
        "checked_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "mode": f"运行中的服务 {args.base_url}" if args.base_url else "每项独立的进程内 HTTP 服务",
        "environment": {"python": platform.python_version(), "platform": platform.platform(), "packages": package_versions()},
        "summary": {"passed": len(cases) - failed - recorded, "failed": failed, "record_only": recorded},
        "cases": [case.as_dict() for case in cases],
    }
    if args.json_path:
        save_report(args.json_path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    if args.markdown_path:
        save_report(args.markdown_path, markdown_report(report))
    print(json.dumps(report["summary"], ensure_ascii=False))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
