# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["starlette==1.10.0", "uvicorn==0.54.0", "httpx==0.28.1"]
# ///

"""Password-protected HTTPS tunnel gateway for the existing local ORD001 service."""

import argparse
import hashlib
import hmac
import html
import secrets
import time
from collections import deque
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.routing import Route

COOKIE = "__Host-ord001_access"
SESSION_SECONDS = 8 * 60 * 60
MAX_JSON_BODY = 16 * 1024
MAX_UPLOAD_BODY = 6 * 1024 * 1024
HOP_HEADERS = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
               "te", "trailer", "transfer-encoding", "upgrade"}
ACCESS_PAGE = Path(__file__).with_name("share") / "access.html"


class WindowLimit:
    def __init__(self, limit, seconds=60):
        self.limit = limit
        self.seconds = seconds
        self.events = deque()

    def allow(self):
        now = time.monotonic()
        while self.events and self.events[0] <= now - self.seconds:
            self.events.popleft()
        if len(self.events) >= self.limit:
            return False
        self.events.append(now)
        return True


def create_app(*, password=None, public_host, upstream="http://127.0.0.1:8024", transport=None,
               model_limit=20, login_limit=30):
    if password is not None and len(password) < 12:
        raise ValueError("共享口令至少需要 12 个字符。")
    public = urlsplit("https://" + public_host)
    if (public.netloc != public_host or not public.hostname or public.port is not None
            or public.username or public.password or public.path or public.query or public.fragment):
        raise ValueError("必须指定不含路径、端口或凭据的公开主机名。")
    origin = urlsplit(upstream)
    if (origin.scheme != "http" or origin.hostname not in ("127.0.0.1", "localhost")
            or origin.username or origin.password or origin.path not in ("", "/")
            or origin.query or origin.fragment):
        raise ValueError("共享入口只能转发到本机 HTTP 服务。")
    upstream = upstream.rstrip("/")
    digest = hashlib.sha256(password.encode()).digest() if password is not None else None
    signing_key = secrets.token_bytes(32) if password is not None else None
    attempts, messages = WindowLimit(login_limit), WindowLimit(model_limit)
    inflight = 0

    def signature(value):
        return hmac.new(signing_key, value.encode(), hashlib.sha256).hexdigest()

    def valid_cookie(value):
        if not value or len(value) > 200:
            return False
        try:
            expiry, nonce, supplied = value.split(".")
            remaining = int(expiry) - int(time.time())
        except (ValueError, TypeError):
            return False
        return (0 < remaining <= SESSION_SECONDS
                and hmac.compare_digest(signature(expiry + "." + nonce), supplied))

    def access_page(next_path, message="", status=200):
        source = ACCESS_PAGE.read_text(encoding="utf-8")
        source = source.replace("{{next}}", html.escape(next_path, quote=True))
        source = source.replace("{{error}}", html.escape(message))
        return HTMLResponse(source, status_code=status, headers={
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'",
            "Cache-Control": "no-store", "Referrer-Policy": "same-origin",
            "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY",
        })

    def problem(code, message, status):
        headers = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}
        if status == 429:
            headers["Retry-After"] = "60"
        return JSONResponse({"error": code, "message": message}, status_code=status, headers=headers)

    @asynccontextmanager
    async def lifespan(app):
        async with httpx.AsyncClient(timeout=45, follow_redirects=False, trust_env=False,
                                     transport=transport) as client:
            app.state.client = client
            yield

    async def gateway(request: Request):
        nonlocal inflight
        host = request.headers.get("host", "")
        if host != public_host:
            return problem("invalid_host", "访问地址不正确。", 400)
        expected_origin = "https://" + public_host
        if request.headers.get("x-forwarded-proto", request.url.scheme) != "https":
            return RedirectResponse(expected_origin + request.url.path, status_code=307)
        if request.headers.get("origin") not in (None, expected_origin):
            return problem("cross_origin", "拒绝跨站请求。", 403)
        path = request.url.path
        authorized = password is None or valid_cookie(request.cookies.get(COOKIE))
        if path == "/_access" and password is None:
            next_path = "/review" if request.query_params.get("next") == "/review" else "/"
            return RedirectResponse(next_path, status_code=303, headers={"Cache-Control": "no-store"})
        if path == "/_access":
            next_path = "/review" if request.query_params.get("next") == "/review" else "/"
            if request.method in ("GET", "HEAD"):
                return RedirectResponse(next_path, status_code=303) if authorized else access_page(next_path)
            if request.method != "POST":
                return problem("method_not_allowed", "请通过页面登录。", 405)
            if not attempts.allow():
                return access_page(next_path, "尝试次数较多，请一分钟后再试。", 429)
            if request.headers.get("content-type", "").split(";")[0] != "application/x-www-form-urlencoded":
                return access_page(next_path, "请通过页面输入访问口令。", 415)
            try:
                values = parse_qs((await request.body()).decode("utf-8"), max_num_fields=3)
            except (UnicodeError, ValueError):
                return access_page(next_path, "请重新输入访问口令。", 400)
            supplied = values.get("password", [""])[0]
            if not hmac.compare_digest(hashlib.sha256(supplied.encode()).digest(), digest):
                return access_page(next_path, "口令不正确，请重试。", 401)
            value = str(int(time.time()) + SESSION_SECONDS) + "." + secrets.token_hex(16)
            response = RedirectResponse(next_path, status_code=303, headers={"Cache-Control": "no-store"})
            response.set_cookie(COOKIE, value + "." + signature(value), max_age=SESSION_SECONDS,
                                secure=True, httponly=True, samesite="lax", path="/")
            return response
        if not authorized:
            if path.startswith("/api/"):
                return problem("access_required", "请刷新页面并输入小组访问口令。", 401)
            next_path = "/review" if path == "/review" else "/"
            return RedirectResponse("/_access?next=" + next_path, status_code=303,
                                    headers={"Cache-Control": "no-store"})
        if path.rstrip("/") == "/api/review/reset":
            return problem("local_only", "共享演示不支持清空数据，请由演示负责人在本机操作。", 403)
        is_message = path.rstrip("/") == "/api/customer/messages" and request.method == "POST"
        if is_message and (inflight >= 2 or not messages.allow()):
            return problem("busy", "当前咨询较多，请稍后再试。", 429)
        if is_message:
            inflight += 1
        try:
            ctype = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
            is_media_upload = (
                path.rstrip("/") == "/api/customer/handoff"
                and request.method == "POST"
                and ctype == "multipart/form-data"
            )
            body = await request.body()
            if not is_media_upload and len(body) > MAX_JSON_BODY:
                return problem("payload_too_large", "请求内容过大。", 413)
            headers = {key: value for key, value in request.headers.items()
                       if key.lower() not in HOP_HEADERS | {"host", "origin", "content-length", "accept-encoding"}
                       and not key.lower().startswith(("x-forwarded-", "cf-"))}
            headers["host"] = origin.netloc
            headers["accept-encoding"] = "identity"
            if request.headers.get("origin"):
                headers["origin"] = upstream
            raw_path = request.scope.get("raw_path", b"/").decode("ascii")
            url = httpx.URL(upstream + raw_path).copy_with(query=request.scope.get("query_string", b""))
            # Build directly: merging a shared client's cookie jar would mix browser identities.
            outgoing = httpx.Request(request.method, url, headers=headers, content=body)
            received = await request.app.state.client.send(outgoing)
            forwarded = {key: value for key, value in received.headers.items()
                         if key.lower() not in HOP_HEADERS | {"content-length", "content-encoding", "set-cookie"}}
            forwarded.update({"Cache-Control": "no-store", "X-Frame-Options": "DENY",
                              "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff"})
            response = Response(received.content, status_code=received.status_code, headers=forwarded)
            for cookie in received.headers.get_list("set-cookie"):
                if "; secure" not in cookie.lower():
                    cookie += "; Secure"
                response.raw_headers.append((b"set-cookie", cookie.encode("latin-1")))
            return response
        except httpx.HTTPError:
            return problem("service_unavailable", "客服暂时无法连接，请稍后重试。", 503)
        finally:
            if is_message:
                inflight -= 1

    return Starlette(routes=[Route("/{path:path}", gateway, methods=["GET", "HEAD", "POST", "OPTIONS"])],
                     lifespan=lifespan, max_body_size=MAX_UPLOAD_BODY)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-host", required=True)
    parser.add_argument("--password-file", help="访问口令文件；与 --open 二选一")
    parser.add_argument("--open", action="store_true", help="不设访问口令：链接即通行证；限流与禁止重置仍生效")
    parser.add_argument("--upstream", default="http://127.0.0.1:8024")
    parser.add_argument("--port", type=int, default=8028)
    args = parser.parse_args()
    if args.open and args.password_file:
        parser.error("--open 与 --password-file 不能同时使用。")
    if not args.open and not args.password_file:
        parser.error("请提供 --password-file，或使用 --open 关闭访问口令。")
    password = None
    if not args.open:
        password_file = Path(args.password_file).expanduser()
        if password_file.stat().st_mode & 0o077:
            parser.error("共享口令文件必须仅由本人读取，请先 chmod 600。")
        password = password_file.read_text(encoding="utf-8").strip()
    app = create_app(password=password, public_host=args.public_host, upstream=args.upstream)
    if args.open:
        print("访问口令：已关闭。链接即通行证，只发小组内部。")
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False, log_level="warning")


if __name__ == "__main__":
    main()
