# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = [
#   "langgraph==1.2.19", "langchain==1.4.9", "langchain-openai==1.7.4",
#   "starlette==1.10.0", "uvicorn==0.54.0", "httpx==0.28.1"
# ]
# ///

"""Check sharing permissions and proxy behavior against isolated simulated services. No live model calls."""

import argparse
import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import httpx
from starlette.testclient import TestClient

from ord001_langchain import ScriptedOrderModel
from ord001_share import COOKIE, SESSION_SECONDS, create_app as share_app
from ord001_web import create_app as web_app
from ord001_web_service import DemoService

BASE = "https://demo.example.test"
PASSWORD = "synthetic-share-check-password"


def run_checks():
    results = []
    service = DemoService(model=ScriptedOrderModel())
    app = share_app(password=PASSWORD, public_host="demo.example.test", model_limit=1,
                    transport=httpx.ASGITransport(web_app(service)))
    with TestClient(app, base_url=BASE, follow_redirects=False) as client:
        def passed(name):
            results.append({"case": name, "status": "passed"})

        def access():
            response = client.post("/_access", data={"password": PASSWORD}, headers={"Origin": BASE})
            assert response.status_code == 303, "Valid shared password was refused"
            return response

        def post(path, data):
            response = client.post(path, json=data, headers={"Origin": BASE})
            assert response.status_code == 200, f"Expected successful proxy request at {path}"
            return response.json()

        assert client.get("/").status_code == 303
        assert client.get("/_access").headers["referrer-policy"] == "same-origin"
        assert client.post("/_access", data={"password": PASSWORD}, headers={"Origin": "null"}).status_code == 403
        for path in ("/api/health", "/api/customer/state", "/api/review/tickets"):
            assert client.get(path).status_code == 401
        assert client.post("/api/customer/messages", json={"text": "hello"}).status_code == 401
        assert not service.store.tickets()
        passed("未授权访问页面、模型和商家接口均受保护")

        wrong = client.post("/_access", data={"password": "wrong-synthetic-input"})
        assert wrong.status_code == 401 and "wrong-synthetic-input" not in wrong.text
        response = access()
        cookie_header = response.headers["set-cookie"].lower()
        assert all(item in cookie_header for item in ("secure", "httponly", "samesite=lax", "path=/"))
        saved = type(client.cookies)(client.cookies)
        token = client.cookies.get(COOKIE)
        client.cookies.clear()
        client.cookies.set(COOKIE, token + "x", domain="demo.example.test", path="/")
        assert client.get("/api/health").status_code == 401
        client.cookies = saved
        future = time.time() + SESSION_SECONDS + 1
        with patch("ord001_share.time.time", return_value=future):
            assert client.get("/api/health").status_code == 401
        client.cookies = saved
        passed("口令错误、篡改及过期会话被拒绝；登录 Cookie 安全属性有效")

        assert client.get("/api/health").status_code == 200
        assert client.get("/").status_code == 200
        assert client.get("/review").status_code == 200
        assert client.get("/static/app.js").status_code == 200
        assert client.get("/api/health", headers={"Host": "other.example.test"}).status_code == 400
        assert client.post("/api/customer/login", json={"customer_id": "U001"},
                           headers={"Origin": "https://other.example.test"}).status_code == 403
        redirect = client.get("http://demo.example.test/_access")
        assert redirect.status_code == 307 and redirect.headers["location"].startswith("https://")
        passed("双端及静态资源转发正常；跨站、错误主机和明文 HTTP 受控")

        post("/api/customer/login", {"customer_id": "U001"})
        first = type(client.cookies)(client.cookies)
        client.cookies.clear()
        access()
        post("/api/customer/login", {"customer_id": "U002"})
        second = type(client.cookies)(client.cookies)
        client.cookies = first
        assert client.get("/api/customer/me").json()["customer"]["customer_id"] == "U001"
        client.cookies.delete("ord001_customer")
        assert client.get("/api/customer/me").status_code == 401
        client.cookies = second
        assert client.get("/api/customer/me").json()["customer"]["customer_id"] == "U002"
        client.cookies = first
        passed("两个浏览器账号互不串号；缺少身份 Cookie 不会复用他人的登录")

        turn = post("/api/customer/messages", {"text": "ORD001 可以申请延误补偿吗？"})
        assert turn["outcome"] == "awaiting_confirmation" and not service.store.tickets()
        post("/api/customer/confirm", {"answer": "confirm"})
        ticket = client.get("/api/customer/tickets").json()["tickets"][0]
        ticket_id = ticket["ticket_id"]
        assert ticket["status"] == "pending" and ticket["coupon_issued_yuan"] is None
        post("/api/review/login", {"reviewer_id": "R001"})
        post(f"/api/review/tickets/{ticket_id}/decision", {"decision": "request_info", "note": "请说明等待情况"})
        assert client.get(f"/api/customer/tickets/{ticket_id}").json()["ticket"]["status"] == "needs_info"
        post(f"/api/customer/tickets/{ticket_id}/information", {"text": "模拟说明：餐品晚到。"})
        post(f"/api/review/tickets/{ticket_id}/decision", {"decision": "approve", "note": "已核实"})
        final = client.get("/api/customer/tickets").json()["tickets"][0]
        assert final["ticket_id"] == ticket_id and final["status"] == "approved"
        assert final["coupon_issued_yuan"] == 10 and len(service.store.tickets()) == 1
        passed("通过网关完成确认建单、商家补问、顾客补充与同票批准")

        for path in ("/api/review/reset", "/api/review/reset/", "/api/review/%72eset"):
            assert client.post(path, json={}, headers={"Origin": BASE}).status_code == 403
        assert len(service.store.tickets()) == 1
        passed("共享入口阻止重置模拟库，原有工单保留")

        limited = client.post("/api/customer/messages", json={"text": "再次咨询"}, headers={"Origin": BASE})
        assert limited.status_code == 429 and limited.headers["retry-after"] == "60"
        oversized = client.post("/api/customer/confirm", content=b"x" * 17000,
                                headers={"Content-Type": "application/json", "Origin": BASE})
        assert oversized.status_code == 413
        passed("模型请求速率和请求体大小限制实际生效")

    def unavailable(request):
        raise httpx.ConnectError("synthetic-private-error-marker", request=request)

    app = share_app(password=PASSWORD, public_host="demo.example.test", transport=httpx.MockTransport(unavailable))
    with TestClient(app, base_url=BASE, follow_redirects=False) as client:
        assert client.post("/_access", data={"password": PASSWORD}).status_code == 303
        response = client.get("/api/health")
        assert response.status_code == 503 and "synthetic-private-error-marker" not in response.text
        assert PASSWORD not in response.text
    results.append({"case": "后端故障返回脱敏提示，不泄露异常或访问口令", "status": "passed"})

    app = share_app(password=PASSWORD, public_host="demo.example.test", login_limit=1)
    with TestClient(app, base_url=BASE, follow_redirects=False) as client:
        assert client.post("/_access", data={"password": "wrong"}).status_code == 401
        assert client.post("/_access", data={"password": "wrong"}).status_code == 429
    results.append({"case": "口令尝试次数限制实际生效", "status": "passed"})

    async def concurrency():
        entered, release = asyncio.Event(), asyncio.Event()
        count = 0

        async def delayed(request):
            nonlocal count
            count += 1
            if count == 2:
                entered.set()
            await release.wait()
            return httpx.Response(200, json={"ok": True})

        app = share_app(password=PASSWORD, public_host="demo.example.test", transport=httpx.MockTransport(delayed))
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url=BASE) as client:
                assert (await client.post("/_access", data={"password": PASSWORD})).status_code == 303
                requests = [asyncio.create_task(client.post("/api/customer/messages", json={"text": "hello"})) for _ in range(2)]
                try:
                    await asyncio.wait_for(entered.wait(), timeout=3)
                    assert (await client.post("/api/customer/messages", json={"text": "third"})).status_code == 429
                finally:
                    release.set()
                    completed = await asyncio.gather(*requests)
                assert all(response.status_code == 200 for response in completed) and count == 2
    asyncio.run(concurrency())
    results.append({"case": "最多两条模型请求同时进入后端，第三条明确返回繁忙", "status": "passed"})

    service = DemoService(model=ScriptedOrderModel())
    app = share_app(password=None, public_host="demo.example.test", model_limit=1,
                    transport=httpx.ASGITransport(web_app(service)))
    with TestClient(app, base_url=BASE, follow_redirects=False) as client:
        assert client.get("/api/health").status_code == 200
        assert client.get("/").status_code == 200
        assert client.get("/review").status_code == 200
        assert client.get("/_access?next=/review").status_code == 303
        assert client.post("/api/review/reset", json={}).status_code == 403
        assert client.get("/api/health", headers={"Host": "other.example.test"}).status_code == 400
        assert client.post("/api/customer/login", json={"customer_id": "U001"},
                           headers={"Origin": "https://other.example.test"}).status_code == 403
        assert not service.store.tickets()
        assert client.post("/api/customer/login", json={"customer_id": "U001"}).status_code == 200
        assert client.post("/api/customer/messages", json={"text": "你好"}).status_code == 200
        assert client.post("/api/customer/messages", json={"text": "再问一次"}).status_code == 429
        handoff = client.post("/api/customer/handoff", json={})
        assert handoff.status_code == 200 and handoff.json()["handoff"]["status"] == "waiting"
        probe = client.get("/static/ping.svg")
        assert probe.status_code == 200 and probe.headers["content-type"].startswith("image/svg+xml")
    results.append({"case": "开放模式直接进入，仍保留重置拦截、主机/同源校验与聊天限流", "status": "passed"})
    results.append({"case": "聊天限流时「转人工」按钮仍可经网关使用；入口探测图片可经网关读取", "status": "passed"})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", required=True)
    args = parser.parse_args()
    results = run_checks()
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "live_model_calls": 0,
              "results": results, "summary": {"passed": len(results), "failed": 0}}
    path = Path(args.json)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
