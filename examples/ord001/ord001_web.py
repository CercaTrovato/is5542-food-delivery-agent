# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = [
#     "langgraph==1.2.19",
#     "langchain==1.4.9",
#     "langchain-openai==1.7.4",
#     "starlette==1.10.0",
#     "uvicorn==0.54.0",
#     "python-multipart==0.0.20",
# ]
# ///

"""Local ORD001 web demo: customer & merchant review workbenches with magic-byte upload checks & SSE streaming."""

import argparse
import asyncio
import json
import logging
import os
import secrets
import threading
from collections import OrderedDict
from pathlib import Path
from urllib.parse import urlsplit

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import MutableHeaders
from starlette.middleware import Middleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response, StreamingResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from ord001_web_service import DemoService, ServiceError

WEB_DIR = Path(__file__).with_name("web")
CUSTOMER_COOKIE, REVIEWER_COOKIE = "ord001_customer", "ord001_reviewer"
MAX_TEXT, MAX_NOTE, MAX_ID = 500, 200, 32
MAX_MEDIA_BYTES = 5 * 1024 * 1024
MAX_SESSIONS = 512
MEDIA_TYPES = {
    "image/jpeg": ("image", "jpg"), "image/png": ("image", "png"), "image/webp": ("image", "webp"),
    "audio/webm": ("audio", "webm"), "audio/ogg": ("audio", "ogg"), "audio/mp4": ("audio", "m4a"),
    "audio/mpeg": ("audio", "mp3"),
}
LOCAL_HOSTS = ("127.0.0.1", "localhost", "testserver")
CSP = "default-src 'self'; base-uri 'none'; form-action 'self'; img-src 'self' blob:; media-src 'self' blob:"


def verify_media_magic(content: bytes, media_type: str) -> bool:
    """Strictly verify binary file header magic bytes to reject spoofed or sub-4-byte malformed uploads."""
    if len(content) < 4:
        return False
    if media_type == "image/jpeg":
        return content.startswith(b"\xff\xd8\xff")
    if media_type == "image/png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    if media_type == "image/webp":
        return len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP"
    if media_type == "audio/ogg":
        return content.startswith(b"OggS")
    if media_type == "audio/webm":
        return content.startswith(b"\x1a\x45\xdf\xa3")
    if media_type == "audio/mp4":
        return len(content) >= 8 and b"ftyp" in content[:16]
    if media_type == "audio/mpeg":
        return content.startswith(b"ID3") or (content[0] == 0xFF and (content[1] & 0xE0) == 0xE0)
    return False


class SecurityHeaders:
    """Same-origin assets only. API responses are never cached."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        is_api = scope["path"].startswith("/api/")

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["X-Content-Type-Options"] = "nosniff"
                headers["Content-Security-Policy"] = CSP
                headers["Referrer-Policy"] = "no-referrer"
                if is_api:
                    headers["Cache-Control"] = "no-store"
                elif "Cache-Control" not in headers:
                    headers["Cache-Control"] = "no-cache"
            await send(message)

        await self.app(scope, receive, send_with_headers)


class Sessions:
    """Bounded LRU server-side sessions. Cookie carries only an opaque random id."""

    def __init__(self, maxsize: int = MAX_SESSIONS):
        self._items: OrderedDict[str, dict] = OrderedDict()
        self._maxsize = maxsize
        self._lock = threading.Lock()

    def open(self, identity: dict) -> str:
        sid = secrets.token_urlsafe(24)
        with self._lock:
            self._items[sid] = identity
            self._items.move_to_end(sid)
            while len(self._items) > self._maxsize:
                self._items.popitem(last=False)
        return sid

    def get(self, sid: str | None) -> dict | None:
        if not sid:
            return None
        with self._lock:
            found = self._items.get(sid)
            if found is not None:
                self._items.move_to_end(sid)
            return found

    def close(self, sid: str | None) -> None:
        if not sid:
            return
        with self._lock:
            self._items.pop(sid, None)


def _check_origin_and_secret(request: Request, *, check_review_secret: bool = False) -> None:
    origin = request.headers.get("origin")
    if origin and urlsplit(origin).netloc != request.headers.get("host"):
        raise ServiceError(403, "cross_origin", "拒绝跨站请求。")
    if check_review_secret:
        required_secret = os.getenv("ORD001_REVIEW_SECRET")
        if required_secret:
            provided = request.headers.get("x-review-secret") or ""
            if not secrets.compare_digest(provided, required_secret):
                raise ServiceError(403, "invalid_review_secret", "缺少有效的管理端安全口令。")


async def read_json(request: Request) -> dict:
    """Accept same-origin JSON only, which also keeps cross-site form posts out."""
    _check_origin_and_secret(request)
    if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
        raise ServiceError(415, "json_required", "请求体必须是 JSON。")
    try:
        body = await request.json()
    except ValueError:
        raise ServiceError(400, "invalid_json", "请求体不是有效的 JSON。") from None
    if not isinstance(body, dict):
        raise ServiceError(400, "invalid_json", "请求体必须是 JSON 对象。")
    return body


def text_field(body: dict, key: str, limit: int, *, required: bool = True) -> str | None:
    value = body.get(key)
    if value is None and not required:
        return None
    if not isinstance(value, str) or (required and not value.strip()):
        raise ServiceError(400, f"invalid_{key}", f"{key} 必须是非空文本。")
    value = value.strip()
    if len(value) > limit:
        raise ServiceError(400, f"{key}_too_long", f"{key} 不能超过 {limit} 个字。")
    return value or None


async def service_error(request: Request, exc: ServiceError) -> JSONResponse:
    return JSONResponse({"error": exc.code, "message": exc.message}, status_code=exc.status)


async def read_handoff(request: Request) -> tuple[str | None, list[dict]]:
    """Read a JSON handoff or a small multipart handoff with magic-byte validated media files."""
    _check_origin_and_secret(request)
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip()
    if content_type == "application/json":
        body = await read_json(request)
        return text_field(body, "text", MAX_TEXT, required=False), []
    if content_type != "multipart/form-data":
        raise ServiceError(415, "upload_required", "附件请求必须使用 multipart/form-data。")
    try:
        async with request.form(max_files=3, max_fields=4, max_part_size=MAX_MEDIA_BYTES) as form:
            text = text_field({"text": form.get("text")}, "text", MAX_TEXT, required=False)
            files = []
            for upload in form.getlist("attachment"):
                media_type = ((getattr(upload, "content_type", None) or "").split(";", 1)[0].strip().lower())
                spec = MEDIA_TYPES.get(media_type)
                if spec is None:
                    raise ServiceError(415, "unsupported_media", "只支持 JPG、PNG、WebP 图片和常见语音格式。")
                content = await upload.read()
                if not content or len(content) > MAX_MEDIA_BYTES:
                    raise ServiceError(413, "media_too_large", "每个附件必须大于 0 且不超过 5 MB。")
                if not verify_media_magic(content, media_type):
                    raise ServiceError(415, "corrupted_or_spoofed_media", "附件文件头校验未通过，请上传真实的图像或语音文件。")
                original = Path(getattr(upload, "filename", None) or ("图片" if spec[0] == "image" else "语音")).name
                files.append({"kind": spec[0], "extension": spec[1], "original_name": original[:120],
                              "media_type": media_type, "content": content})
            return text, files
    except ServiceError:
        raise
    except Exception as exc:
        raise ServiceError(400, "invalid_multipart", "附件请求无法读取，请重新选择文件。") from exc


async def no_icon(request: Request) -> Response:
    return Response(status_code=204)


def page(name: str):
    async def endpoint(request: Request) -> FileResponse:
        return FileResponse(WEB_DIR / name, headers={"Cache-Control": "no-cache"})

    return endpoint


def create_app(service: DemoService | None = None, allowed_hosts=LOCAL_HOSTS) -> Starlette:
    service = service or DemoService()
    sessions = Sessions()

    def identity(request: Request, role: str) -> dict:
        cookie = CUSTOMER_COOKIE if role == "customer" else REVIEWER_COOKIE
        found = sessions.get(request.cookies.get(cookie))
        if not found or found["role"] != role:
            raise ServiceError(401, "login_required", "请先登录模拟账号。")
        return found

    def signed_in(request: Request, cookie: str, ident: dict, payload: dict) -> JSONResponse:
        sessions.close(request.cookies.get(cookie))
        response = JSONResponse(payload)
        response.set_cookie(cookie, sessions.open(ident), httponly=True, samesite="lax")
        # Separation-of-Duties (SoD): prevent same browser holding customer + reviewer roles in strict/prod mode.
        if os.getenv("ORD001_PRODUCTION_MODE") == "1" or os.getenv("ORD001_STRICT_SOD") == "1":
            other = REVIEWER_COOKIE if cookie == CUSTOMER_COOKIE else CUSTOMER_COOKIE
            sessions.close(request.cookies.get(other))
            response.delete_cookie(other, httponly=True, samesite="lax")
        return response

    def signed_out(request: Request, cookie: str) -> JSONResponse:
        sessions.close(request.cookies.get(cookie))
        response = JSONResponse({"ok": True})
        response.delete_cookie(cookie, httponly=True, samesite="lax")
        return response

    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", **service.info()})

    async def customer_login(request: Request) -> JSONResponse:
        customer = service.data.customers.get(text_field(await read_json(request), "customer_id", MAX_ID))
        if customer is None:
            raise ServiceError(400, "unknown_customer", "没有这个模拟顾客。")
        cid = customer["customer_id"]
        ident = {"role": "customer", "customer_id": cid, "thread_id": f"web-{cid}-{secrets.token_hex(6)}"}
        return signed_in(request, CUSTOMER_COOKIE, ident, {"customer": customer})

    async def customer_logout(request: Request) -> JSONResponse:
        await read_json(request)
        return signed_out(request, CUSTOMER_COOKIE)

    async def customer_me(request: Request) -> JSONResponse:
        ident = identity(request, "customer")
        return JSONResponse({"customer": service.data.customers[ident["customer_id"]]})

    async def customer_orders(request: Request) -> JSONResponse:
        ident = identity(request, "customer")
        return JSONResponse({"orders": service.customer_orders(ident["customer_id"])})

    async def customer_state(request: Request) -> JSONResponse:
        ident = identity(request, "customer")
        return JSONResponse(await run_in_threadpool(service.customer_view, ident["thread_id"], ident["customer_id"]))

    async def customer_message(request: Request) -> JSONResponse:
        ident = identity(request, "customer")
        text = text_field(await read_json(request), "text", MAX_TEXT)
        return JSONResponse(await run_in_threadpool(service.send_message, ident["thread_id"], ident["customer_id"], text))

    async def customer_message_stream(request: Request) -> StreamingResponse:
        """True async LangGraph SSE streaming endpoint with real-time token-level clause buffering & reply_risk guard."""
        ident = identity(request, "customer")
        text = text_field(await read_json(request), "text", MAX_TEXT)

        async def event_gen():
            try:
                async for evt in service.stream_message(ident["thread_id"], ident["customer_id"], text):
                    yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
            except ServiceError as exc:
                yield f"data: {json.dumps({'type': 'error', 'error': exc.code, 'message': exc.message}, ensure_ascii=False)}\n\n"

        return StreamingResponse(event_gen(), media_type="text/event-stream")

    async def customer_goodwill(request: Request) -> JSONResponse:
        ident = identity(request, "customer")
        order_id = text_field(await read_json(request), "order_id", MAX_ID)
        return JSONResponse(await run_in_threadpool(service.claim_goodwill_care, ident["customer_id"], order_id))

    async def customer_confirm(request: Request) -> JSONResponse:
        ident = identity(request, "customer")
        answer = (await read_json(request)).get("answer")
        return JSONResponse(await run_in_threadpool(service.confirm, ident["thread_id"], ident["customer_id"], answer))

    async def customer_tickets(request: Request) -> JSONResponse:
        ident = identity(request, "customer")
        return JSONResponse({"tickets": service.customer_tickets(ident["customer_id"])})

    async def customer_ticket(request: Request) -> JSONResponse:
        ident = identity(request, "customer")
        return JSONResponse(service.customer_ticket(ident["customer_id"], request.path_params["ticket_id"]))

    async def customer_information(request: Request) -> JSONResponse:
        ident = identity(request, "customer")
        text = text_field(await read_json(request), "text", MAX_TEXT)
        return JSONResponse(await run_in_threadpool(service.submit_information, ident["customer_id"],
                                                    request.path_params["ticket_id"], text))

    async def customer_rating(request: Request) -> JSONResponse:
        ident = identity(request, "customer")
        rating = (await read_json(request)).get("rating")
        return JSONResponse(await run_in_threadpool(service.rate_ticket, ident["customer_id"],
                                                    request.path_params["ticket_id"], rating))

    async def customer_handoff(request: Request) -> JSONResponse:
        ident = identity(request, "customer")
        text, files = await read_handoff(request)
        return JSONResponse(await run_in_threadpool(service.request_handoff, ident["thread_id"], ident["customer_id"], text, files))

    async def media(request: Request) -> FileResponse:
        attachment_id = request.path_params["attachment_id"]
        customer = sessions.get(request.cookies.get(CUSTOMER_COOKIE))
        reviewer = sessions.get(request.cookies.get(REVIEWER_COOKIE))
        if customer and customer.get("role") == "customer":
            found = service.media_for(attachment_id, customer_id=customer["customer_id"])
        elif reviewer and reviewer.get("role") == "reviewer":
            found = service.media_for(attachment_id, reviewer=True, reviewer_id=reviewer["reviewer_id"])
        else:
            raise ServiceError(401, "login_required", "请先登录模拟账号。")
        return FileResponse(found["path"], media_type=found["media_type"], headers={"Cache-Control": "no-store"})

    async def customer_handoff_cancel(request: Request) -> JSONResponse:
        ident = identity(request, "customer")
        await read_json(request)
        return JSONResponse(await run_in_threadpool(service.cancel_handoff, ident["thread_id"], ident["customer_id"],
                                                    request.path_params["handoff_id"]))

    async def customer_handoff_followup(request: Request) -> JSONResponse:
        ident = identity(request, "customer")
        text = text_field(await read_json(request), "text", MAX_TEXT)
        return JSONResponse(await run_in_threadpool(service.customer_handoff_followup, ident["thread_id"],
                                                    ident["customer_id"], request.path_params["handoff_id"], text))

    async def review_login(request: Request) -> JSONResponse:
        _check_origin_and_secret(request, check_review_secret=True)
        reviewer = service.data.reviewers.get(text_field(await read_json(request), "reviewer_id", MAX_ID))
        if reviewer is None:
            raise ServiceError(400, "unknown_reviewer", "没有这个模拟审批员。")
        ident = {"role": "reviewer", "reviewer_id": reviewer["reviewer_id"]}
        return signed_in(request, REVIEWER_COOKIE, ident, {"reviewer": reviewer})

    async def review_logout(request: Request) -> JSONResponse:
        await read_json(request)
        return signed_out(request, REVIEWER_COOKIE)

    async def review_me(request: Request) -> JSONResponse:
        ident = identity(request, "reviewer")
        return JSONResponse({"reviewer": service.data.reviewers[ident["reviewer_id"]]})

    async def review_tickets(request: Request) -> JSONResponse:
        ident = identity(request, "reviewer")
        return JSONResponse(await run_in_threadpool(service.review_tickets, ident["reviewer_id"]))

    async def review_analytics(request: Request) -> JSONResponse:
        ident = identity(request, "reviewer")
        return JSONResponse(await run_in_threadpool(service.analytics, ident["reviewer_id"]))

    async def review_stp_mode(request: Request) -> JSONResponse:
        ident = identity(request, "reviewer")
        body = await read_json(request)
        return JSONResponse(await run_in_threadpool(service.set_stp_mode, bool(body.get("enabled")), ident["reviewer_id"]))

    async def review_stp_batch(request: Request) -> JSONResponse:
        ident = identity(request, "reviewer")
        await read_json(request)
        return JSONResponse(await run_in_threadpool(service.batch_approve_green_stp, ident["reviewer_id"]))

    async def review_ticket(request: Request) -> JSONResponse:
        ident = identity(request, "reviewer")
        return JSONResponse(await run_in_threadpool(service.review_detail, request.path_params["ticket_id"], ident["reviewer_id"]))

    async def review_decision(request: Request) -> JSONResponse:
        ident = identity(request, "reviewer")
        body = await read_json(request)
        note = text_field(body, "note", MAX_NOTE, required=False)
        ticket_id = request.path_params["ticket_id"]
        return JSONResponse(await run_in_threadpool(service.decide, ticket_id, ident["reviewer_id"],
                                                    body.get("decision"), note))

    async def review_runs(request: Request) -> JSONResponse:
        identity(request, "reviewer")
        return JSONResponse({"runs": service.runs()})

    async def review_handoffs(request: Request) -> JSONResponse:
        ident = identity(request, "reviewer")
        return JSONResponse(await run_in_threadpool(service.review_handoffs, ident["reviewer_id"]))

    async def review_handoff_reply(request: Request) -> JSONResponse:
        ident = identity(request, "reviewer")
        text = text_field(await read_json(request), "text", MAX_TEXT)
        return JSONResponse(await run_in_threadpool(service.reply_handoff, request.path_params["handoff_id"],
                                                    ident["reviewer_id"], text))

    async def review_handoff_followup(request: Request) -> JSONResponse:
        ident = identity(request, "reviewer")
        text = text_field(await read_json(request), "text", MAX_TEXT)
        return JSONResponse(await run_in_threadpool(service.followup_handoff, request.path_params["handoff_id"],
                                                    ident["reviewer_id"], text))

    async def review_reset(request: Request) -> JSONResponse:
        identity(request, "reviewer")
        _check_origin_and_secret(request, check_review_secret=True)
        await read_json(request)
        await run_in_threadpool(service.reset)
        return JSONResponse({"ok": True})

    routes = [
        Route("/", page("customer.html")),
        Route("/review", page("review.html")),
        Route("/favicon.ico", no_icon),
        Route("/api/health", health),
        Route("/api/customer/login", customer_login, methods=["POST"]),
        Route("/api/customer/logout", customer_logout, methods=["POST"]),
        Route("/api/customer/me", customer_me),
        Route("/api/customer/orders", customer_orders),
        Route("/api/customer/state", customer_state),
        Route("/api/customer/messages", customer_message, methods=["POST"]),
        Route("/api/customer/messages/stream", customer_message_stream, methods=["POST"]),
        Route("/api/customer/goodwill", customer_goodwill, methods=["POST"]),
        Route("/api/customer/confirm", customer_confirm, methods=["POST"]),
        Route("/api/customer/tickets", customer_tickets),
        Route("/api/customer/tickets/{ticket_id}", customer_ticket),
        Route("/api/customer/tickets/{ticket_id}/information", customer_information, methods=["POST"]),
        Route("/api/customer/tickets/{ticket_id}/rating", customer_rating, methods=["POST"]),
        Route("/api/customer/handoff", customer_handoff, methods=["POST"]),
        Route("/api/customer/handoffs/{handoff_id}/cancel", customer_handoff_cancel, methods=["POST"]),
        Route("/api/customer/handoffs/{handoff_id}/followup", customer_handoff_followup, methods=["POST"]),
        Route("/api/media/{attachment_id}", media),
        Route("/api/review/login", review_login, methods=["POST"]),
        Route("/api/review/logout", review_logout, methods=["POST"]),
        Route("/api/review/me", review_me),
        Route("/api/review/tickets", review_tickets),
        Route("/api/review/analytics", review_analytics),
        Route("/api/review/stp-mode", review_stp_mode, methods=["POST"]),
        Route("/api/review/stp-batch", review_stp_batch, methods=["POST"]),
        Route("/api/review/tickets/{ticket_id}", review_ticket),
        Route("/api/review/tickets/{ticket_id}/decision", review_decision, methods=["POST"]),
        Route("/api/review/handoffs", review_handoffs),
        Route("/api/review/handoffs/{handoff_id}/reply", review_handoff_reply, methods=["POST"]),
        Route("/api/review/handoffs/{handoff_id}/followup", review_handoff_followup, methods=["POST"]),
        Route("/api/review/runs", review_runs),
        Route("/api/review/reset", review_reset, methods=["POST"]),
        Mount("/static", StaticFiles(directory=WEB_DIR), name="static"),
    ]
    middleware = [Middleware(TrustedHostMiddleware, allowed_hosts=list(allowed_hosts)), Middleware(SecurityHeaders)]
    app = Starlette(routes=routes, middleware=middleware, exception_handlers={ServiceError: service_error},
                    max_body_size=6 * 1024 * 1024)
    app.state.service = service
    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8024)
    parser.add_argument("--db", default=":memory:", help="工单与状态机 SQLite 文件。指定路径即可跨重启持久化")
    parser.add_argument("--log-file", help="把每轮运行记录按 JSON 行追加到这个文件")
    parser.add_argument("--model-config", help="本机私有模型 JSON 配置路径；不要把含密钥的文件放进仓库")
    args = parser.parse_args()

    import uvicorn

    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    run_log = logging.getLogger("ord001_web")
    run_log.setLevel(logging.INFO)
    if args.log_file:
        run_log.addHandler(logging.FileHandler(args.log_file, encoding="utf-8"))
    service = DemoService(db_path=args.db, model_config_path=args.model_config)
    policy = service.policy
    local = args.host in LOCAL_HOSTS
    base = f"http://{args.host}:{args.port}"
    print(f"顾客入口：{base}/")
    print(f"审批入口：{base}/review")
    print(f"规则版本：{policy.version}（threshold_minutes={policy.threshold_minutes}，"
          f"include_threshold={policy.include_threshold}，coupon_yuan={policy.coupon_yuan}）")
    print(f"模型：{service.model_label}　订单数据：{service.data.version}")
    if not local:
        if not os.getenv("ORD001_REVIEW_SECRET"):
            generated_secret = secrets.token_urlsafe(18)
            os.environ["ORD001_REVIEW_SECRET"] = generated_secret
            print("安全加固：非回环地址启动已默认启用 Fail-Closed 管理端随机口令保护（ORD001_REVIEW_SECRET 已生成）。")
        os.environ.setdefault("ORD001_STRICT_SOD", "1")
    app = create_app(service, allowed_hosts=LOCAL_HOSTS if local else ("*",))
    uvicorn.run(app, host=args.host, port=args.port, access_log=False)


if __name__ == "__main__":
    main()
