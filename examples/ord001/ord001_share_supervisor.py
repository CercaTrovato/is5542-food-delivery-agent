# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = []
# ///

"""Keep the ORD001 group share online: Quick Tunnel → gateway → the fixed Surge entry page.

Meant to run under launchd. It starts cloudflared and the open gateway, waits until the new public
host answers through Cloudflare, then publishes the Surge redirect page that points to it. It rebuilds
the tunnel when Cloudflare deletes it ("Tunnel not found"), when cloudflared exits, or when the public
check fails for several minutes, with growing pauses between failed attempts. The Surge token stays in
its private file and reaches only the Surge CLI, through that one process's environment.
"""

import argparse
import json
import os
import re
import signal
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
GATEWAY_MARK = "ord001_share.py --public-host"
# Local checks must not go through a system proxy.
LOCAL = urllib.request.build_opener(urllib.request.ProxyHandler({}))
# Quick Tunnel names are several words joined by hyphens; api.trycloudflare.com must not match.
HOST_PATTERN = re.compile(r"https://([a-z0-9]+(?:-[a-z0-9]+)+\.trycloudflare\.com)")
IPV4 = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
TUNNEL_GONE = b"Tunnel not found"
FALLBACK_NAMESERVERS = ("kevin.ns.cloudflare.com", "marjory.ns.cloudflare.com")
CHECK_SECONDS = 30           # how often the running share is checked
FAIL_REBUILD_SECONDS = 300   # public check failing this long in a row → new tunnel
BUILD_SPACING_SECONDS = 180  # never ask Cloudflare for tunnels faster than this
DNS_WAIT_SECONDS = 360       # a new host must answer within this time
SURGE_CHECK_SECONDS = 600    # how often the Surge entry is compared with the current host
MAX_BACKOFF_SECONDS = 1800


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sh(args, timeout, env=None) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout, env=env,
                              stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(args, 124, "", "timed out")


class BuildFailed(Exception):
    """A tunnel attempt that did not come up; the supervisor pauses and tries again."""


class Supervisor:
    def __init__(self, args):
        self.args = args
        self.runtime = Path(args.runtime_dir).expanduser()
        self.logs = self.runtime / "logs"
        self.logs.mkdir(parents=True, exist_ok=True)
        self.site = self.runtime / "surge-site"
        self.tunnel = self.gateway = self.awake = None
        self.host = None
        self.servers = list(FALLBACK_NAMESERVERS)
        self.watch_files = {}
        self.tunnel_mark = f"cloudflared tunnel --url http://127.0.0.1:{args.gateway_port} "
        self.stopping = False
        self.last_build = 0.0
        self.status = {"state": "starting", "host": None, "builds": 0, "surge_ok": None, "started_at": now(),
                       "surge": f"https://{args.domain}/"}

    def log(self, message, **extra):
        print(json.dumps({"at": now(), "message": message, **extra}, ensure_ascii=False), flush=True)

    def update(self, **values):
        """Write the current state to status.json so anyone can see what the share is doing."""
        self.status.update(values, updated_at=now())
        target = self.runtime / "status.json"
        temp = target.with_suffix(".tmp")
        temp.write_text(json.dumps(self.status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temp.replace(target)

    def pause(self, seconds):
        end = time.monotonic() + seconds
        while not self.stopping and time.monotonic() < end:
            time.sleep(max(0.0, min(1.0, end - time.monotonic())))

    # Child processes

    def spawn(self, args, log_name):
        out = open(self.logs / log_name, "ab")
        try:
            # Same process group as the supervisor: stopping the supervisor's group stops these too.
            return subprocess.Popen(args, stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                    env=dict(os.environ))
        finally:
            out.close()

    @staticmethod
    def end(process):
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    @staticmethod
    def sweep(pattern):
        sh(["/usr/bin/pkill", "-f", pattern], 10)

    def stop_gateway(self):
        self.end(self.gateway)
        self.gateway = None
        # uv runs the gateway as its own child; make sure nothing is left holding the port.
        self.sweep(GATEWAY_MARK)

    def stop_tunnel(self):
        self.end(self.tunnel)
        self.tunnel = None
        self.sweep(self.tunnel_mark)

    def teardown(self):
        self.stop_gateway()
        self.stop_tunnel()

    # Checks

    def web_ok(self) -> bool:
        try:
            with LOCAL.open(f"http://127.0.0.1:{self.args.web_port}/api/health", timeout=10) as response:
                return response.status == 200
        except OSError:
            return False

    def gateway_up(self, host) -> bool:
        request = urllib.request.Request(f"http://127.0.0.1:{self.args.gateway_port}/api/health",
                                         headers={"Host": host, "X-Forwarded-Proto": "https"})
        try:
            with LOCAL.open(request, timeout=10):
                return True
        except urllib.error.HTTPError:
            return True  # It answered; a 503 only means the web app behind it is down.
        except OSError:
            return False

    def nameservers(self) -> list[str]:
        found = sh(["/usr/bin/dig", "+short", "NS", "trycloudflare.com"], 15).stdout.split()
        return [name.rstrip(".") for name in found if name.endswith(".")][:2] or list(FALLBACK_NAMESERVERS)

    @staticmethod
    def lookup(host, server) -> list[str]:
        answer = sh(["/usr/bin/dig", "+short", "+time=3", "+tries=1", f"@{server}", host, "A"], 15).stdout
        return IPV4.findall(answer)

    def public_ok(self, host) -> bool:
        """Ask Cloudflare's own name servers, so no resolver cache hides a new or deleted host, then call it."""
        found = next((ips for ips in (self.lookup(host, server) for server in self.servers) if ips), [])
        if not found:
            return False
        result = sh(["/usr/bin/curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "20",
                     "--resolve", f"{host}:443:{found[0]}", f"https://{host}/api/health"], 30)
        return result.stdout.strip() == "200"

    # Tunnel and gateway

    def start_tunnel(self) -> str:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        logfile, console = self.logs / f"tunnel-{stamp}.log", f"tunnel-{stamp}.console.log"
        self.tunnel = self.spawn([self.args.cloudflared, "tunnel", "--url", f"http://127.0.0.1:{self.args.gateway_port}",
                                  "--protocol", "http2", "--no-autoupdate", "--logfile", str(logfile)], console)
        self.watch_files = {logfile: 0, self.logs / console: 0}
        deadline = time.monotonic() + 90
        while not self.stopping and time.monotonic() < deadline:
            if self.tunnel.poll() is not None:
                raise BuildFailed(f"cloudflared exited with code {self.tunnel.returncode}")
            for path in self.watch_files:
                if path.exists():
                    match = HOST_PATTERN.search(path.read_text(encoding="utf-8", errors="replace"))
                    if match:
                        return match.group(1)
            self.pause(2)
        raise BuildFailed("cloudflared did not report a public host within 90 seconds")

    def tunnel_gone(self) -> bool:
        """True once cloudflared logs that Cloudflare deleted this tunnel on its side."""
        gone = False
        for path, offset in list(self.watch_files.items()):
            if not path.exists():
                continue
            with path.open("rb") as handle:
                handle.seek(offset)
                chunk = handle.read()
            self.watch_files[path] = offset + len(chunk)
            gone = gone or TUNNEL_GONE in chunk
        return gone

    def start_gateway(self, host):
        self.stop_gateway()
        self.gateway = self.spawn([self.args.uv, "run", "--no-project", "--python", "3.12", str(HERE / "ord001_share.py"),
                                   "--public-host", host, "--open", "--port", str(self.args.gateway_port),
                                   "--upstream", f"http://127.0.0.1:{self.args.web_port}"], "gateway.log")
        deadline = time.monotonic() + 120
        while not self.stopping and time.monotonic() < deadline:
            if self.gateway.poll() is not None:
                raise BuildFailed(f"gateway exited with code {self.gateway.returncode}")
            if self.gateway_up(host):
                return
            self.pause(2)
        raise BuildFailed("gateway did not start within 120 seconds")

    # Surge entry

    def render_site(self, host):
        page = (HERE / "share" / "entry.html").read_text(encoding="utf-8").replace("__LIVE_ORIGIN__", f"https://{host}")
        for name in ("index.html", "200.html"):
            temp = self.site / f".{name}.tmp"
            temp.write_text(page, encoding="utf-8")
            temp.replace(self.site / name)

    def publish(self, host) -> bool:
        try:
            return self._publish(host)
        except Exception as exc:  # a Surge problem must never take the tunnel down with it
            self.log("surge publish error", error=type(exc).__name__)
            return False

    def _publish(self, host) -> bool:
        self.render_site(host)
        secret = json.loads(Path(self.args.token_file).expanduser().read_text(encoding="utf-8"))
        env = {**os.environ, "SURGE_TOKEN": secret["token"]}
        result = sh([self.args.node, self.args.surge_cli, "publish", str(self.site), self.args.domain], 240, env)
        text = ANSI.sub("", result.stdout + "\n" + result.stderr)
        for private in (secret.get("token"), secret.get("email")):
            if private:
                text = text.replace(private, "[hidden]")
        tail = [line.strip() for line in text.splitlines() if line.strip()][-3:]
        ok = result.returncode == 0 and "Success" in text
        self.log("surge publish " + ("ok" if ok else "failed"), code=result.returncode, tail=tail)
        return ok and self.surge_points_to(host, attempts=6)

    def surge_points_to(self, host, attempts=1) -> bool:
        for attempt in range(attempts):
            pages = [sh(["/usr/bin/curl", "-sS", "--max-time", "20", f"https://{self.args.domain}{path}"], 30).stdout
                     for path in ("/", "/review")]
            if all(f"https://{host}" in page for page in pages):
                return True
            if attempt + 1 < attempts:
                self.pause(10)
        return False

    # Main loop

    def build(self) -> str:
        """One attempt: new tunnel, gateway for its host, wait until it answers publicly, then publish."""
        wait = BUILD_SPACING_SECONDS - (time.monotonic() - self.last_build)
        if self.last_build and wait > 0:
            self.log("waiting before asking Cloudflare for another tunnel", seconds=round(wait))
            self.pause(wait)
        self.last_build = time.monotonic()
        self.teardown()
        self.update(state="building", builds=self.status["builds"] + 1)
        self.servers = self.nameservers()
        host = self.start_tunnel()
        self.log("tunnel host assigned", host=host)
        self.start_gateway(host)
        deadline = time.monotonic() + DNS_WAIT_SECONDS
        while not self.public_ok(host):
            if self.stopping:
                raise BuildFailed("stopping")
            if self.tunnel.poll() is not None or self.tunnel_gone():
                raise BuildFailed("tunnel was dropped before it went live")
            if time.monotonic() > deadline:
                raise BuildFailed(f"public host did not answer within {DNS_WAIT_SECONDS} seconds")
            self.pause(10)
        self.log("public host answers", host=host)
        self.host = host
        (self.runtime / "public-url.txt").write_text(f"https://{host}\n", encoding="utf-8")
        surge_ok = self.publish(host)
        self.update(state="online" if surge_ok else "online_surge_pending", host=host, surge_ok=surge_ok,
                    since=now(), last_ok=now())
        return host

    def watch(self):
        """Watch a live share. Returns the reason it needs a new tunnel."""
        failing_since = None
        next_surge = time.monotonic() + (SURGE_CHECK_SECONDS if self.status.get("surge_ok") else 120)
        while not self.stopping:
            self.pause(CHECK_SECONDS)
            if self.stopping:
                return "stopping"
            if self.tunnel.poll() is not None:
                return f"cloudflared exited ({self.tunnel.returncode})"
            if self.tunnel_gone():
                return "Cloudflare deleted the tunnel"
            if self.gateway.poll() is not None:
                self.log("gateway exited; restarting it", code=self.gateway.returncode)
                try:
                    self.start_gateway(self.host)
                except BuildFailed as exc:
                    return f"gateway restart failed: {exc}"
            if not self.web_ok():
                # The web app is launchd's job. A new tunnel would not help, so only record it.
                self.update(state="web_down")
                continue
            if self.public_ok(self.host):
                failing_since = None
                state = "online" if self.status.get("surge_ok") else "online_surge_pending"
                self.update(state=state, last_ok=now())
            else:
                failing_since = failing_since or time.monotonic()
                down = time.monotonic() - failing_since
                self.update(state="reconnecting", failing_seconds=round(down))
                if down > FAIL_REBUILD_SECONDS:
                    return f"public check failing for {round(down)} seconds"
            if time.monotonic() >= next_surge:
                ok = self.surge_points_to(self.host)
                if not ok:
                    self.log("Surge entry does not point to the current host; publishing again")
                    ok = self.publish(self.host)
                self.update(surge_ok=ok)
                # A failed publish is retried every two minutes; a healthy entry is rechecked every ten.
                next_surge = time.monotonic() + (SURGE_CHECK_SECONDS if ok else 120)
        return "stopping"

    def stop(self, *_):
        self.stopping = True

    def run(self):
        signal.signal(signal.SIGTERM, self.stop)
        signal.signal(signal.SIGINT, self.stop)
        self.teardown()  # a gateway or tunnel left behind by an earlier run
        self.awake = subprocess.Popen(["/usr/bin/caffeinate", "-i", "-w", str(os.getpid())],
                                      stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        backoff = 60
        try:
            while not self.stopping:
                if not self.web_ok():
                    self.update(state="waiting_for_web")
                    self.pause(15)
                    continue
                try:
                    self.build()
                    backoff = 60
                    reason = self.watch()
                except Exception as exc:  # one bad attempt must not end the supervisor
                    if self.stopping:
                        break
                    detail = str(exc) if isinstance(exc, BuildFailed) else f"{type(exc).__name__}: {exc}"
                    self.log("tunnel attempt failed", reason=detail, retry_in=backoff)
                    self.teardown()
                    self.update(state="retrying", reason=detail, retry_in=backoff)
                    self.pause(backoff)
                    backoff = min(backoff * 2, MAX_BACKOFF_SECONDS)
                    continue
                if reason != "stopping":
                    self.log("rebuilding tunnel", reason=reason)
                    self.update(state="rebuilding", reason=reason)
        finally:
            self.teardown()
            self.end(self.awake)
            self.update(state="stopped")


def main():
    home = Path.home()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-dir", default=str(home / "is5542-dev/share-runtime"))
    parser.add_argument("--domain", default="ord001-group24.surge.sh")
    parser.add_argument("--web-port", type=int, default=8024)
    parser.add_argument("--gateway-port", type=int, default=8028)
    parser.add_argument("--cloudflared", default=str(home / "is5542-dev/share-runtime/cloudflared"))
    parser.add_argument("--uv", default=str(home / ".local/bin/uv"))
    parser.add_argument("--node", default=str(home / ".local/bin/node"))
    parser.add_argument("--surge-cli", default=str(home / "is5542-dev/share-tools/node_modules/surge/bin/surge"))
    parser.add_argument("--token-file", default=str(home / "is5542-dev/share-runtime/surge-token.json"))
    args = parser.parse_args()
    if Path(args.token_file).expanduser().stat().st_mode & 0o077:
        parser.error("Surge 令牌文件必须仅本人可读，请先 chmod 600。")
    Supervisor(args).run()


if __name__ == "__main__":
    main()
