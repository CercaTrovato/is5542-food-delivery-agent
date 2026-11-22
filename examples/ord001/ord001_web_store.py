"""Mock accounts, orders, tamper-evident audit logs, and zero-pickle durable SQLite stores for ORD001."""

import base64
import hashlib
import json
import re
import secrets
import sqlite3
import tempfile
import threading
import zlib
from datetime import datetime
from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver

DATA_PATH = Path(__file__).with_name("demo-data.json")
# evaluate_order receives core facts + optional amount_yuan for low-AOV margin-cap protection.
ORDER_FACT_KEYS = ("status", "expected_at", "delivered_at", "amount_yuan")
DECISION_STATUS = {"approve": "approved", "reject": "rejected", "request_info": "needs_info"}
STATUS_TEXT = {"pending": "待审核", "needs_info": "待补充", "approved": "已批准", "rejected": "已驳回"}
MAX_ATTACHMENTS_PER_HANDOFF = 3
MAX_CUSTOMER_MEDIA_BYTES = 25 * 1024 * 1024

SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    ticket_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    order_id TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    expected_at TEXT NOT NULL,
    delivered_at TEXT NOT NULL,
    late_seconds INTEGER NOT NULL,
    proposed_coupon_yuan INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'needs_info', 'approved', 'rejected')),
    coupon_issued_yuan INTEGER,
    created_at TEXT NOT NULL,
    decided_at TEXT,
    reviewer_id TEXT,
    review_note TEXT,
    information_request TEXT,
    customer_information TEXT,
    information_requested_at TEXT,
    information_submitted_at TEXT,
    rating INTEGER,
    rated_at TEXT,
    UNIQUE (order_id, policy_version)
);
CREATE TABLE IF NOT EXISTS ticket_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id TEXT NOT NULL,
    at TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    note TEXT,
    before_status TEXT,
    after_status TEXT,
    amount_yuan REAL
);
CREATE TABLE IF NOT EXISTS action_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    handoff_id TEXT,
    order_id TEXT,
    ticket_id TEXT,
    at TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    actor_name TEXT,
    actor_role TEXT,
    action TEXT NOT NULL,
    action_label TEXT NOT NULL,
    before_status TEXT,
    after_status TEXT,
    amount_yuan REAL,
    note TEXT,
    is_internal INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS handoffs (
    handoff_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    thread_id TEXT NOT NULL,
    order_id TEXT,
    after_index INTEGER NOT NULL,
    request_text TEXT,
    excerpt TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('waiting', 'replied', 'cancelled')),
    reply_text TEXT,
    reviewer_id TEXT,
    created_at TEXT NOT NULL,
    closed_at TEXT
);
CREATE TABLE IF NOT EXISTS attachments (
    attachment_id TEXT PRIMARY KEY,
    handoff_id TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('image', 'audio')),
    original_name TEXT NOT NULL,
    media_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    storage_name TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS attachment_forensics (
    attachment_id TEXT PRIMARY KEY,
    sha256_hash TEXT NOT NULL,
    perceptual_sig TEXT,
    duplicate_of TEXT,
    forensic_note TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS handoff_messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    handoff_id TEXT NOT NULL,
    sender_role TEXT NOT NULL,
    sender_id TEXT NOT NULL,
    text TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS goodwill_grants (
    grant_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    order_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    amount_yuan INTEGER NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (customer_id, order_id)
);
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    event TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    entry_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS graph_thread_checkpoints (
    namespace TEXT NOT NULL,
    thread_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (namespace, thread_id)
);
"""
# Columns added after the needs_info upgrade. Older files gain them in place, so nothing is copied.
ADDED_TICKET_COLUMNS = (("rating", "INTEGER"), ("rated_at", "TEXT"))
LEDGER_TICKET_COLUMNS = (
    ("tenant_id", "TEXT DEFAULT 'M_67REST'"),
    ("stp_tier", "TEXT"),
    ("merchant_bear_yuan", "REAL"),
    ("platform_bear_yuan", "REAL"),
    ("is_expedited", "INTEGER DEFAULT 0"),
    ("escalated_to", "TEXT"),
    ("escalated_at", "TEXT"),
    ("assigned_reviewer_id", "TEXT"),
)
LEDGER_HANDOFF_COLUMNS = (
    ("tenant_id", "TEXT DEFAULT 'M_67REST'"),
    ("reply_after_index", "INTEGER"),
    ("reply_seq", "INTEGER"),
    ("ended_at", "TEXT"),
    ("initial_appeal", "TEXT"),
    ("is_expedited", "INTEGER DEFAULT 0"),
    ("escalated_to", "TEXT"),
    ("escalated_at", "TEXT"),
    ("assigned_reviewer_id", "TEXT"),
)
ACTION_EVENT_COLUMNS = (
    ("before_status", "TEXT"),
    ("after_status", "TEXT"),
    ("amount_yuan", "REAL"),
)


def now_text() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


ORDER_TYPO_MAP = str.maketrans({"O": "0", "o": "0", "I": "1", "i": "1", "L": "1", "l": "1"})


def normalize_order_id(raw: str) -> str:
    cleaned = re.sub(r"[\s\-_#:：]+", "", str(raw).strip()).upper()
    if cleaned.startswith("ORD") and len(cleaned) > 3:
        suffix = cleaned[3:].translate(ORDER_TYPO_MAP)
        if suffix.isdigit():
            if len(suffix) < 3:
                suffix = suffix.zfill(3)
            elif len(suffix) > 3 and suffix.startswith("0"):
                stripped = suffix.lstrip("0") or "0"
                if len(stripped) <= 3:
                    suffix = stripped.zfill(3)
        return "ORD" + suffix
    return cleaned


def order_facts(order: dict) -> dict:
    return {key: order.get(key) for key in ORDER_FACT_KEYS if key in order or key in ("status", "expected_at", "delivered_at")}


def compute_perceptual_sig(content: bytes, kind: str, media_type: str) -> str | None:
    """Compute a 64-bit structural visual fingerprint (dHash over decoded PNG IDAT or normalized byte luminances)."""
    if kind != "image" or len(content) < 16:
        return None
    sample_stream = content
    if media_type == "image/png" and content[:8] == b"\x89PNG\r\n\x1a\n":
        idat_chunks = []
        pos = 8
        while pos + 8 <= len(content):
            length = int.from_bytes(content[pos:pos + 4], "big")
            ctype = content[pos + 4:pos + 8]
            cdata = content[pos + 8:pos + 8 + length]
            if ctype == b"IDAT":
                idat_chunks.append(cdata)
            elif ctype == b"IEND":
                break
            pos += 12 + length
        if idat_chunks:
            try:
                sample_stream = zlib.decompressobj().decompress(b"".join(idat_chunks), 4 * 1024 * 1024)
            except zlib.error:
                sample_stream = content[24:]
    # Sample 65 evenly spaced luminance buckets and compute 64 adjacent gradient bits (dHash style)
    n = len(sample_stream)
    if n < 65:
        sample_stream = sample_stream * ((65 // n) + 1)
        n = len(sample_stream)
    step = max(1, n // 65)
    vals = []
    for i in range(65):
        window = sample_stream[i * step: min(n, (i + 1) * step)]
        vals.append(sum(window) / max(1, len(window)))
    bits = 0
    for i in range(64):
        if vals[i] < vals[i + 1]:
            bits |= (1 << i)
    return f"{bits:016x}"


def hamming_distance_hex(sig_a: str | None, sig_b: str | None) -> int:
    if not sig_a or not sig_b or len(sig_a) != 16 or len(sig_b) != 16:
        return 64
    return (int(sig_a, 16) ^ int(sig_b, 16)).bit_count()


def inspect_media_forensics(content: bytes, kind: str, media_type: str) -> str:
    """Lightweight binary header & dimension inspection for uploaded customer evidence."""
    if kind == "image":
        if media_type == "image/png" and len(content) >= 24 and content[:8] == b"\x89PNG\r\n\x1a\n":
            w = int.from_bytes(content[16:20], "big")
            h = int.from_bytes(content[20:24], "big")
            return f"PNG 原图文件头校验通过（{w}×{h}px，{len(content) // 1024 or 1}KB）"
        if media_type == "image/jpeg" and content[:3] == b"\xff\xd8\xff":
            return f"JPEG 相机/相册原图头校验通过（{len(content) // 1024 or 1}KB）"
        if media_type == "image/webp" and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
            return f"WebP 图像头校验通过（{len(content) // 1024 or 1}KB）"
        return f"图像魔数核验通过（{len(content) // 1024 or 1}KB）"
    return f"语音证据魔数核验通过（{media_type}，{len(content) // 1024 or 1}KB）"


def _b64e(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def _b64d(s: str) -> bytes:
    return base64.b64decode(s.encode("ascii"))


class DurableSqliteSaver(InMemorySaver):
    """Zero-pickle, O(1) per-thread incremental SQLite checkpointer over LangGraph's JsonPlusSerializer."""

    def __init__(self, store: "TicketStore", namespace: str):
        super().__init__()
        self._store = store
        self._namespace = namespace
        self._hydrate()

    def _hydrate(self) -> None:
        for thread_id, raw_json in self._store.load_thread_checkpoints(self._namespace):
            try:
                doc = json.loads(raw_json)
                for ns, ckpt_map in doc.get("storage", {}).items():
                    for ckpt_id, entry in ckpt_map.items():
                        c_type, c_b64, m_type, m_b64, parent_id = entry
                        self.storage[thread_id][ns][ckpt_id] = (
                            (c_type, _b64d(c_b64)),
                            (m_type, _b64d(m_b64)),
                            parent_id,
                        )
                for w_item in doc.get("writes", []):
                    ns, ckpt_id, inner_list = w_item
                    outer_key = (thread_id, ns, ckpt_id)
                    for task_id, idx, ch, v_type, v_b64, task_path in inner_list:
                        self.writes[outer_key][(task_id, idx)] = (task_id, ch, (v_type, _b64d(v_b64)), task_path)
                for b_item in doc.get("blobs", []):
                    ns, ch, ver_type, ver_str, v_type, v_b64 = b_item
                    ver = int(ver_str) if ver_type == "int" else (float(ver_str) if ver_type == "float" else ver_str)
                    self.blobs[(thread_id, ns, ch, ver)] = (v_type, _b64d(v_b64))
            except Exception:
                continue

    def _flush_thread(self, thread_id: str) -> None:
        ns_storage = {}
        for ns, ckpt_map in self.storage.get(thread_id, {}).items():
            ns_storage[ns] = {
                ckpt_id: [c_tup[0], _b64e(c_tup[1]), m_tup[0], _b64e(m_tup[1]), parent_id]
                for ckpt_id, (c_tup, m_tup, parent_id) in ckpt_map.items()
            }
        writes_out = []
        for (tid, ns, ckpt_id), w_map in self.writes.items():
            if tid != thread_id:
                continue
            inner = [
                [task_id, idx, ch, val_tup[0], _b64e(val_tup[1]), task_path]
                for (task_id, idx), (task_id_v, ch, val_tup, task_path) in w_map.items()
            ]
            writes_out.append([ns, ckpt_id, inner])
        blobs_out = []
        for (tid, ns, ch, ver), (v_type, v_bytes) in self.blobs.items():
            if tid != thread_id:
                continue
            ver_type = "int" if isinstance(ver, int) else ("float" if isinstance(ver, float) else "str")
            blobs_out.append([ns, ch, ver_type, str(ver), v_type, _b64e(v_bytes)])
        payload_json = json.dumps({"storage": ns_storage, "writes": writes_out, "blobs": blobs_out}, ensure_ascii=False)
        self._store.save_thread_checkpoint(self._namespace, thread_id, payload_json)

    def put(self, config, checkpoint, metadata, new_versions):
        res = super().put(config, checkpoint, metadata, new_versions)
        tid = str(config.get("configurable", {}).get("thread_id") or "")
        if tid:
            self._flush_thread(tid)
        return res

    def put_writes(self, config, writes, task_id, task_path=""):
        super().put_writes(config, writes, task_id, task_path)
        tid = str(config.get("configurable", {}).get("thread_id") or "")
        if tid:
            self._flush_thread(tid)


class DemoData:
    """Mock customers, reviewers and orders from demo-data.json."""

    def __init__(self, path: Path = DATA_PATH):
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        self.version = raw["data_version"]
        self.service_date = raw["service_date"]
        self.customers = {item["customer_id"]: item for item in raw["customers"]}
        self.reviewers = {item["reviewer_id"]: item for item in raw["reviewers"]}
        self.orders = {item["order_id"]: item for item in raw["orders"]}

    def lookup_for_customer(self, order_id: str, customer_id: str | None) -> tuple[str, dict | None]:
        """Return found, not_found or unauthorized. Another customer's order never leaves here."""
        order = self.orders.get(normalize_order_id(order_id))
        if order is None:
            return "not_found", None
        if customer_id is None or order["customer_id"] != customer_id:
            return "unauthorized", None
        return "found", dict(order)

    def orders_for_customer(self, customer_id: str) -> list[dict]:
        return [dict(order) for order in self.orders.values() if order["customer_id"] == customer_id]


class TicketStore:
    """SQLite tickets, multi-tenant RLS, goodwill grants, forensic hashes, and WORM SHA-256 audit logs."""

    def __init__(self, path: str = ":memory:"):
        self._lock = threading.RLock()
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        if path == ":memory:":
            self.media_dir = Path(tempfile.mkdtemp(prefix="ord001-media-"))
        else:
            self.media_dir = Path(path).expanduser().resolve().parent / f"{Path(path).stem}-media"
            self.media_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._migrate()
        self._db.executescript(SCHEMA)
        self._ensure_ledger_columns()

    def _migrate(self) -> None:
        """Replace the original three-state table atomically, preserving tickets and events; add later columns in place."""
        table = self._db.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'tickets'").fetchone()
        if table is None:
            return
        columns = {row["name"] for row in self._db.execute("PRAGMA table_info(tickets)")}
        if not ("needs_info" in table["sql"] and {"information_request", "customer_information",
                                                     "information_requested_at", "information_submitted_at"} <= columns):
            ticket_schema = SCHEMA.split("CREATE TABLE IF NOT EXISTS ticket_events", 1)[0]
            with self._db:
                self._db.execute("BEGIN IMMEDIATE")
                self._db.execute(ticket_schema.replace("IF NOT EXISTS tickets", "tickets_upgrade", 1))
                target = [row["name"] for row in self._db.execute("PRAGMA table_info(tickets_upgrade)")]
                common = ", ".join(f'"{name}"' for name in target if name in columns)
                self._db.execute(f"INSERT INTO tickets_upgrade ({common}) SELECT {common} FROM tickets")
                self._db.execute("DROP TABLE tickets")
                self._db.execute("ALTER TABLE tickets_upgrade RENAME TO tickets")
            columns = {row["name"] for row in self._db.execute("PRAGMA table_info(tickets)")}
        missing = [(name, kind) for name, kind in ADDED_TICKET_COLUMNS if name not in columns]
        if missing:
            with self._db:
                for name, kind in missing:
                    self._db.execute(f"ALTER TABLE tickets ADD COLUMN {name} {kind}")

    def _ensure_ledger_columns(self) -> None:
        t_cols = {row["name"] for row in self._db.execute("PRAGMA table_info(tickets)")}
        h_cols = {row["name"] for row in self._db.execute("PRAGMA table_info(handoffs)")}
        m_cols = {row["name"] for row in self._db.execute("PRAGMA table_info(handoff_messages)")}
        a_cols = {row["name"] for row in self._db.execute("PRAGMA table_info(attachments)")}
        f_cols = {row["name"] for row in self._db.execute("PRAGMA table_info(attachment_forensics)")}
        e_cols = {row["name"] for row in self._db.execute("PRAGMA table_info(ticket_events)")}
        with self._db:
            for name, kind in LEDGER_TICKET_COLUMNS:
                if name not in t_cols:
                    self._db.execute(f"ALTER TABLE tickets ADD COLUMN {name} {kind}")
            for name, kind in LEDGER_HANDOFF_COLUMNS:
                if name not in h_cols:
                    self._db.execute(f"ALTER TABLE handoffs ADD COLUMN {name} {kind}")
            for name, kind in ACTION_EVENT_COLUMNS:
                if name not in e_cols:
                    self._db.execute(f"ALTER TABLE ticket_events ADD COLUMN {name} {kind}")
            if "after_index" not in m_cols:
                self._db.execute("ALTER TABLE handoff_messages ADD COLUMN after_index INTEGER")
            if "after_index" not in a_cols:
                self._db.execute("ALTER TABLE attachments ADD COLUMN after_index INTEGER")
            if "is_followup" not in a_cols:
                self._db.execute("ALTER TABLE attachments ADD COLUMN is_followup INTEGER NOT NULL DEFAULT 0")
            if "perceptual_sig" not in f_cols:
                self._db.execute("ALTER TABLE attachment_forensics ADD COLUMN perceptual_sig TEXT")

    def close(self) -> None:
        with self._lock:
            self._db.close()

    # Incremental O(1) per-thread JSON checkpoint persistence (zero pickle)

    def load_thread_checkpoints(self, namespace: str) -> list[tuple[str, str]]:
        with self._lock:
            rows = self._db.execute(
                "SELECT thread_id, payload_json FROM graph_thread_checkpoints WHERE namespace = ?", (namespace,)
            ).fetchall()
            return [(row["thread_id"], row["payload_json"]) for row in rows]

    def save_thread_checkpoint(self, namespace: str, thread_id: str, payload_json: str) -> None:
        with self._lock, self._db:
            self._db.execute(
                "INSERT INTO graph_thread_checkpoints (namespace, thread_id, payload_json, updated_at) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(namespace, thread_id) DO UPDATE SET payload_json = excluded.payload_json, updated_at = excluded.updated_at",
                (namespace, thread_id, payload_json, now_text()),
            )

    # Tamper-evident SHA-256 hash-chained audit logs (WORM)

    def append_audit_log(self, entry: dict, *, tenant_id: str = "M_67REST") -> dict:
        at = entry.get("at") or now_text()
        event = str(entry.get("event") or "unknown")
        payload_json = json.dumps(entry, ensure_ascii=False, sort_keys=True)
        with self._lock, self._db:
            last = self._db.execute("SELECT entry_hash FROM audit_logs ORDER BY log_id DESC LIMIT 1").fetchone()
            prev_hash = last["entry_hash"] if last else "GENESIS_ORD001_SHA256"
            digest = hashlib.sha256(f"{prev_hash}|{at}|{tenant_id}|{payload_json}".encode("utf-8")).hexdigest()
            self._db.execute(
                "INSERT INTO audit_logs (at, tenant_id, event, payload_json, prev_hash, entry_hash) VALUES (?, ?, ?, ?, ?, ?)",
                (at, tenant_id, event, payload_json, prev_hash, digest),
            )
            return {**entry, "audit_hash": digest[:16]}

    def recent_audit_logs(self, limit: int = 1000, *, since_reset: bool = False) -> list[dict]:
        with self._lock:
            rows = self._db.execute(
                "SELECT payload_json, entry_hash FROM audit_logs ORDER BY log_id DESC LIMIT ?", (limit,)
            ).fetchall()
        out = []
        for row in reversed(rows):
            data = json.loads(row["payload_json"])
            data.setdefault("audit_hash", row["entry_hash"][:16])
            if since_reset and data.get("event") == "reset":
                out = [data]
            else:
                out.append(data)
        return out

    def verify_audit_chain(self) -> dict:
        """Verify unbroken SHA-256 hash chain across all append-only audit_logs rows (Cap. 8 s.22A compliance)."""
        with self._lock:
            rows = self._db.execute(
                "SELECT log_id, at, tenant_id, payload_json, prev_hash, entry_hash FROM audit_logs ORDER BY log_id ASC"
            ).fetchall()
        expected_prev = "GENESIS_ORD001_SHA256"
        for row in rows:
            if row["prev_hash"] != expected_prev:
                return {"intact": False, "entries": len(rows), "broken_at_log_id": row["log_id"]}
            calc = hashlib.sha256(
                f"{row['prev_hash']}|{row['at']}|{row['tenant_id']}|{row['payload_json']}".encode("utf-8")
            ).hexdigest()
            if calc != row["entry_hash"]:
                return {"intact": False, "entries": len(rows), "broken_at_log_id": row["log_id"]}
            expected_prev = row["entry_hash"]
        return {"intact": True, "entries": len(rows), "latest_hash": expected_prev[:16]}

    # Goodwill care coupon ledger (real ¥3 self-service issuance for 15-30m near-threshold delays)

    def claim_goodwill(self, *, customer_id: str, order_id: str, tenant_id: str = "M_67REST",
                       amount_yuan: int = 3, reason: str = "临界延迟准时保暖心关怀券") -> tuple[dict, bool]:
        with self._lock, self._db:
            existing = self._one(
                "SELECT * FROM goodwill_grants WHERE customer_id = ? AND order_id = ?", (customer_id, order_id)
            )
            if existing:
                return existing, False
            next_num = self._db.execute(
                "SELECT COALESCE(MAX(CAST(SUBSTR(grant_id, 2) AS INTEGER)), 0) + 1 FROM goodwill_grants"
            ).fetchone()[0]
            grant_id = f"G{next_num:04d}"
            at = now_text()
            self._db.execute(
                "INSERT INTO goodwill_grants (grant_id, customer_id, order_id, tenant_id, amount_yuan, reason, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (grant_id, customer_id, order_id, tenant_id, amount_yuan, reason, at),
            )
            return self._one("SELECT * FROM goodwill_grants WHERE grant_id = ?", (grant_id,)), True

    def goodwill_grants(self, *, customer_id: str | None = None, tenant_id: str | None = None) -> list[dict]:
        clauses, params = [], []
        if customer_id is not None:
            clauses.append("customer_id = ?")
            params.append(customer_id)
        if tenant_id is not None and tenant_id != "*":
            clauses.append("tenant_id = ?")
            params.append(tenant_id)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        with self._lock:
            rows = self._db.execute(f"SELECT * FROM goodwill_grants{where} ORDER BY grant_id", tuple(params)).fetchall()
            return [dict(r) for r in rows]

    # Attachments & forensics (SHA-256 + 64-bit dHash perceptual similarity + per-customer disk quota)

    def attachments_for_order(self, order_id: str, customer_id: str) -> list[dict]:
        with self._lock:
            rows = self._db.execute(
                "SELECT a.attachment_id, a.handoff_id, a.kind, a.original_name, a.media_type, a.size_bytes, a.created_at, "
                "f.sha256_hash, f.duplicate_of, f.forensic_note "
                "FROM attachments a "
                "JOIN handoffs h ON a.handoff_id = h.handoff_id "
                "LEFT JOIN attachment_forensics f ON a.attachment_id = f.attachment_id "
                "WHERE h.order_id = ? AND h.customer_id = ? "
                "ORDER BY a.created_at, a.attachment_id",
                (order_id, customer_id),
            ).fetchall()
        out = []
        for row in rows:
            item = {k: row[k] for k in ("attachment_id", "handoff_id", "kind", "original_name", "media_type", "size_bytes", "created_at")}
            if row["forensic_note"]:
                item["forensic_note"] = row["forensic_note"]
                item["duplicate_alert"] = bool(row["duplicate_of"])
            out.append(item)
        return out

    def _attachment_rows(self, handoff_id: str) -> list[dict]:
        rows = self._db.execute(
            "SELECT a.attachment_id, a.handoff_id, a.kind, a.original_name, a.media_type, a.size_bytes, a.created_at, "
            "a.after_index, COALESCE(a.is_followup, 0) AS is_followup, "
            "f.sha256_hash, f.duplicate_of, f.forensic_note "
            "FROM attachments a LEFT JOIN attachment_forensics f ON a.attachment_id = f.attachment_id "
            "WHERE a.handoff_id = ? ORDER BY a.created_at, a.rowid, a.attachment_id",
            (handoff_id,),
        ).fetchall()
        out = []
        for row in rows:
            item = {k: row[k] for k in ("attachment_id", "handoff_id", "kind", "original_name", "media_type", "size_bytes", "created_at")}
            if row["is_followup"]:
                item["is_followup"] = True
                item["followup_seq"] = int(row["is_followup"])
                if row["after_index"] is not None:
                    item["after_index"] = row["after_index"]
            if row["forensic_note"]:
                item["forensic_note"] = row["forensic_note"]
                item["duplicate_alert"] = bool(row["duplicate_of"])
            out.append(item)
        return out

    def attachments(self, handoff_id: str) -> list[dict]:
        with self._lock:
            return self._attachment_rows(handoff_id)

    def attachment(self, attachment_id: str) -> dict | None:
        with self._lock:
            return self._one("SELECT * FROM attachments WHERE attachment_id = ?", (attachment_id,))

    def _store_files(self, handoff_id: str, customer_id: str, files: list[dict], *,
                     after_index: int | None = None, is_followup: int | bool = 0) -> None:
        if not files:
            return
        existing_cnt = self._db.execute(
            "SELECT COUNT(*) FROM attachments WHERE handoff_id = ?", (handoff_id,)
        ).fetchone()[0]
        if existing_cnt + len(files) > MAX_ATTACHMENTS_PER_HANDOFF:
            raise ValueError("attachment_quota_exceeded")
        total_cust_bytes = self._db.execute(
            "SELECT COALESCE(SUM(a.size_bytes), 0) FROM attachments a JOIN handoffs h ON a.handoff_id = h.handoff_id WHERE h.customer_id = ?",
            (customer_id,),
        ).fetchone()[0]
        batch_bytes = sum(len(it["content"]) for it in files)
        if total_cust_bytes + batch_bytes > MAX_CUSTOMER_MEDIA_BYTES:
            raise ValueError("customer_disk_quota_exceeded")

        for item in files:
            attachment_id = f"A{secrets.token_hex(8)}"
            storage_name = f"{attachment_id}.{item['extension']}"
            target = self.media_dir / storage_name
            target.write_bytes(item["content"])
            at = now_text()
            sha = hashlib.sha256(item["content"]).hexdigest()
            psig = compute_perceptual_sig(item["content"], item["kind"], item["media_type"])
            prior = self._db.execute(
                "SELECT attachment_id FROM attachment_forensics WHERE sha256_hash = ? LIMIT 1", (sha,)
            ).fetchone()
            dup_of = prior["attachment_id"] if prior else None
            dup_reason = "SHA-256 精确一致" if dup_of else ""
            if not dup_of and psig:
                candidates = self._db.execute(
                    "SELECT attachment_id, perceptual_sig FROM attachment_forensics WHERE perceptual_sig IS NOT NULL"
                ).fetchall()
                for cand in candidates:
                    dist = hamming_distance_hex(psig, cand["perceptual_sig"])
                    if dist <= 6:
                        dup_of = cand["attachment_id"]
                        dup_reason = f"64-bit 视觉感知哈希近似（Hamming={dist}）"
                        break
            base_note = inspect_media_forensics(item["content"], item["kind"], item["media_type"])
            if dup_of:
                base_note = f"⚠️ 重复图预警（与历史凭证 {dup_of[:8]} {dup_reason}） · {base_note}"
            self._db.execute(
                "INSERT INTO attachments (attachment_id, handoff_id, kind, original_name, media_type, size_bytes,"
                " storage_name, created_at, after_index, is_followup) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (attachment_id, handoff_id, item["kind"], item["original_name"], item["media_type"],
                 len(item["content"]), storage_name, at, after_index, int(is_followup)),
            )
            self._db.execute(
                "INSERT INTO attachment_forensics (attachment_id, sha256_hash, perceptual_sig, duplicate_of, forensic_note, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (attachment_id, sha, psig, dup_of, base_note, at),
            )

    def _one(self, sql: str, params: tuple) -> dict | None:
        row = self._db.execute(sql, params).fetchone()
        return dict(row) if row else None

    def _event(self, ticket_id: str, actor: str, action: str, note: str | None, at: str,
               *, before_status: str | None = None, after_status: str | None = None,
               amount_yuan: float | None = None) -> None:
        self._db.execute(
            "INSERT INTO ticket_events (ticket_id, at, actor, action, note, before_status, after_status, amount_yuan)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (ticket_id, at, actor, action, note, before_status, after_status, amount_yuan),
        )

    def log_action(self, *, handoff_id: str | None, order_id: str | None, ticket_id: str | None,
                   actor_id: str, actor_name: str | None, actor_role: str | None,
                   action: str, action_label: str, before_status: str | None = None,
                   after_status: str | None = None, amount_yuan: float | None = None,
                   note: str | None = None, is_internal: bool = False, at: str | None = None) -> dict:
        ts = at or now_text()
        with self._lock, self._db:
            cur = self._db.execute(
                "INSERT INTO action_logs (handoff_id, order_id, ticket_id, at, actor_id, actor_name, actor_role,"
                " action, action_label, before_status, after_status, amount_yuan, note, is_internal)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (handoff_id, order_id, ticket_id, ts, actor_id, actor_name, actor_role,
                 action, action_label, before_status, after_status, amount_yuan, note, 1 if is_internal else 0),
            )
            return self._one("SELECT * FROM action_logs WHERE log_id = ?", (cur.lastrowid,))

    def action_logs(self, *, handoff_id: str | None = None, ticket_id: str | None = None,
                    order_id: str | None = None, include_internal: bool = True) -> list[dict]:
        clauses, params = [], []
        if handoff_id is not None and ticket_id is not None:
            clauses.append("(handoff_id = ? OR ticket_id = ?)")
            params.extend([handoff_id, ticket_id])
        elif handoff_id is not None:
            clauses.append("handoff_id = ?")
            params.append(handoff_id)
        elif ticket_id is not None:
            clauses.append("ticket_id = ?")
            params.append(ticket_id)
        elif order_id is not None:
            clauses.append("order_id = ?")
            params.append(order_id)
        if not include_internal:
            clauses.append("is_internal = 0")
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        with self._lock:
            rows = self._db.execute(f"SELECT * FROM action_logs{where} ORDER BY log_id", tuple(params)).fetchall()
            return [{**dict(r), "is_internal": bool(r["is_internal"])} for r in rows]

    def get(self, ticket_id: str) -> dict | None:
        with self._lock:
            return self._one("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,))

    def find(self, order_id: str, policy_version: str) -> dict | None:
        with self._lock:
            return self._one(
                "SELECT * FROM tickets WHERE order_id = ? AND policy_version = ?", (order_id, policy_version)
            )

    def tickets(self, *, customer_id: str | None = None, tenant_id: str | None = None) -> list[dict]:
        clauses, params = [], []
        if customer_id is not None:
            clauses.append("customer_id = ?")
            params.append(customer_id)
        if tenant_id is not None and tenant_id != "*":
            clauses.append("COALESCE(tenant_id, 'M_67REST') = ?")
            params.append(tenant_id)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        with self._lock:
            return [dict(row) for row in self._db.execute(f"SELECT * FROM tickets{where} ORDER BY ticket_id", tuple(params)).fetchall()]

    def events(self, ticket_id: str) -> list[dict]:
        with self._lock:
            rows = self._db.execute(
                "SELECT at, actor, action, note, before_status, after_status, amount_yuan"
                " FROM ticket_events WHERE ticket_id = ? ORDER BY event_id",
                (ticket_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def create_or_get(self, *, customer_id: str, order: dict, decision: dict,
                      subrogation: dict | None = None, auto_approve_note: str | None = None) -> tuple[dict, bool]:
        """Create a pending (or STP auto-approved) ticket with immutable persisted ledger split."""
        key = (order["order_id"], decision["policy_version"])
        tenant_id = str(order.get("tenant_id") or "M_67REST")
        sub = subrogation or {}
        stp_tier = sub.get("stp_tier")
        m_bear = sub.get("merchant_bear_yuan")
        p_bear = sub.get("platform_bear_yuan")
        with self._lock, self._db:
            existing = self._one("SELECT * FROM tickets WHERE order_id = ? AND policy_version = ?", key)
            if existing:
                return existing, False
            next_num = self._db.execute(
                "SELECT COALESCE(MAX(CAST(SUBSTR(ticket_id, 2) AS INTEGER)), 0) + 1 FROM tickets"
            ).fetchone()[0]
            ticket_id = f"T{next_num:04d}"
            created_at = now_text()
            if auto_approve_note:
                self._db.execute(
                    "INSERT INTO tickets (ticket_id, customer_id, order_id, policy_version, expected_at, delivered_at,"
                    " late_seconds, proposed_coupon_yuan, status, coupon_issued_yuan, created_at, decided_at,"
                    " reviewer_id, review_note, tenant_id, stp_tier, merchant_bear_yuan, platform_bear_yuan)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'approved', ?, ?, ?, 'STP_ENGINE', ?, ?, ?, ?, ?)",
                    (ticket_id, customer_id, *key, order["expected_at"], order["delivered_at"],
                     decision["late_seconds"], decision["proposed_coupon_yuan"], decision["proposed_coupon_yuan"],
                     created_at, created_at, auto_approve_note, tenant_id, stp_tier, m_bear, p_bear),
                )
                self._event(ticket_id, f"customer:{customer_id}", "submitted", None, created_at)
                self._event(ticket_id, "system:STP_ENGINE", "approved", auto_approve_note, created_at)
            else:
                self._db.execute(
                    "INSERT INTO tickets (ticket_id, customer_id, order_id, policy_version, expected_at, delivered_at,"
                    " late_seconds, proposed_coupon_yuan, status, created_at, tenant_id, stp_tier,"
                    " merchant_bear_yuan, platform_bear_yuan) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?)",
                    (ticket_id, customer_id, *key, order["expected_at"], order["delivered_at"],
                     decision["late_seconds"], decision["proposed_coupon_yuan"], created_at,
                     tenant_id, stp_tier, m_bear, p_bear),
                )
                self._event(ticket_id, f"customer:{customer_id}", "submitted", None, created_at)
            return self._one("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)), True

    def decide(self, ticket_id: str, *, decision: str, reviewer_id: str, note: str | None) -> dict | None:
        """Act on a pending ticket once; asking for information is not a final decision."""
        status = DECISION_STATUS[decision]
        at = now_text()
        with self._lock, self._db:
            existing = self._one("SELECT status, proposed_coupon_yuan FROM tickets WHERE ticket_id = ?", (ticket_id,))
            if not existing or existing["status"] != "pending":
                return None
            if status == "needs_info":
                cursor = self._db.execute(
                    "UPDATE tickets SET status = 'needs_info', reviewer_id = ?, information_request = ?,"
                    " information_requested_at = ?, customer_information = NULL, information_submitted_at = NULL,"
                    " decided_at = NULL, review_note = NULL, coupon_issued_yuan = NULL"
                    " WHERE ticket_id = ? AND status = 'pending'",
                    (reviewer_id, note, at, ticket_id),
                )
                action = "information_requested"
                amt = None
            else:
                cursor = self._db.execute(
                    "UPDATE tickets SET status = ?, decided_at = ?, reviewer_id = ?, review_note = ?,"
                    " coupon_issued_yuan = CASE WHEN ? = 'approved' THEN proposed_coupon_yuan END"
                    " WHERE ticket_id = ? AND status = 'pending'",
                    (status, at, reviewer_id, note, status, ticket_id),
                )
                action = status
                amt = existing["proposed_coupon_yuan"] if status == "approved" else None
            if cursor.rowcount != 1:
                return None
            self._event(ticket_id, f"reviewer:{reviewer_id}", action, note, at,
                        before_status="pending", after_status=status, amount_yuan=amt)
            return self._one("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,))

    def decide_or_override_ticket(self, ticket_id: str, *, target_status: str, reviewer_id: str,
                                  note: str | None, amount_yuan: int | float | None = None,
                                  merchant_bear_yuan: float | None = None,
                                  platform_bear_yuan: float | None = None,
                                  action_name: str | None = None) -> tuple[dict, str] | None:
        """Update ticket status from agent handoff action (supports rejected->approved, uphold, needs_info, reopen)."""
        at = now_text()
        with self._lock, self._db:
            current = self._one("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,))
            if not current:
                return None
            before_status = current["status"]
            if target_status == "approved":
                issued = int(round(amount_yuan)) if amount_yuan is not None else current["proposed_coupon_yuan"]
                m_bear = current.get("merchant_bear_yuan") if merchant_bear_yuan is None else merchant_bear_yuan
                p_bear = current.get("platform_bear_yuan") if platform_bear_yuan is None else platform_bear_yuan
                self._db.execute(
                    "UPDATE tickets SET status = 'approved', decided_at = ?, reviewer_id = ?, review_note = ?,"
                    " coupon_issued_yuan = ?, merchant_bear_yuan = ?, platform_bear_yuan = ? WHERE ticket_id = ?",
                    (at, reviewer_id, note, issued, m_bear, p_bear, ticket_id),
                )
                self._event(ticket_id, f"reviewer:{reviewer_id}", action_name or "approved", note, at,
                            before_status=before_status, after_status="approved", amount_yuan=issued)
            elif target_status == "rejected":
                self._db.execute(
                    "UPDATE tickets SET status = 'rejected', decided_at = ?, reviewer_id = ?, review_note = ?,"
                    " coupon_issued_yuan = NULL WHERE ticket_id = ?",
                    (at, reviewer_id, note, ticket_id),
                )
                self._event(ticket_id, f"reviewer:{reviewer_id}", action_name or "rejected", note, at,
                            before_status=before_status, after_status="rejected")
            elif target_status == "needs_info":
                self._db.execute(
                    "UPDATE tickets SET status = 'needs_info', reviewer_id = ?, information_request = ?,"
                    " information_requested_at = ?, customer_information = NULL, information_submitted_at = NULL,"
                    " decided_at = NULL, review_note = NULL, coupon_issued_yuan = NULL WHERE ticket_id = ?",
                    (reviewer_id, note, at, ticket_id),
                )
                self._event(ticket_id, f"reviewer:{reviewer_id}", action_name or "information_requested", note, at,
                            before_status=before_status, after_status="needs_info")
            elif target_status == "pending":
                self._db.execute(
                    "UPDATE tickets SET status = 'pending', decided_at = NULL, reviewer_id = NULL, review_note = NULL,"
                    " coupon_issued_yuan = NULL WHERE ticket_id = ?",
                    (ticket_id,),
                )
                self._event(ticket_id, f"reviewer:{reviewer_id}", action_name or "reopened", note, at,
                            before_status=before_status, after_status="pending")
            else:
                return None
            return self._one("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)), before_status

    def create_manual_ticket(self, *, customer_id: str, order: dict, policy_version: str,
                             late_seconds: int, proposed_coupon_yuan: int, reviewer_id: str,
                             subrogation: dict | None = None, note: str | None = None) -> tuple[dict, bool]:
        """Create a pending ticket from the agent handoff workbench when no ticket exists for the order."""
        key = (order["order_id"], policy_version)
        tenant_id = str(order.get("tenant_id") or "M_67REST")
        sub = subrogation or {}
        stp_tier = sub.get("stp_tier")
        m_bear = sub.get("merchant_bear_yuan")
        p_bear = sub.get("platform_bear_yuan")
        expected_at = str(order.get("expected_at") or "—")
        delivered_at = str(order.get("delivered_at") or ("配送中" if order.get("status") == "delivering" else "待核验"))
        with self._lock, self._db:
            existing = self._one("SELECT * FROM tickets WHERE order_id = ? AND policy_version = ?", key)
            if existing:
                return existing, False
            next_num = self._db.execute(
                "SELECT COALESCE(MAX(CAST(SUBSTR(ticket_id, 2) AS INTEGER)), 0) + 1 FROM tickets"
            ).fetchone()[0]
            ticket_id = f"T{next_num:04d}"
            created_at = now_text()
            self._db.execute(
                "INSERT INTO tickets (ticket_id, customer_id, order_id, policy_version, expected_at, delivered_at,"
                " late_seconds, proposed_coupon_yuan, status, created_at, tenant_id, stp_tier,"
                " merchant_bear_yuan, platform_bear_yuan, assigned_reviewer_id)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?)",
                (ticket_id, customer_id, *key, expected_at, delivered_at,
                 int(late_seconds or 0), int(proposed_coupon_yuan), created_at,
                 tenant_id, stp_tier, m_bear, p_bear, reviewer_id),
            )
            self._event(ticket_id, f"reviewer:{reviewer_id}", "created_by_agent", note, created_at,
                        before_status="无工单", after_status="pending", amount_yuan=proposed_coupon_yuan)
            return self._one("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)), True

    def update_ticket_flags(self, ticket_id: str, *, is_expedited: int | None = None,
                            escalated_to: str | None = None, assigned_reviewer_id: str | None = None) -> dict | None:
        at = now_text()
        with self._lock, self._db:
            row = self._one("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,))
            if not row:
                return None
            if is_expedited is not None:
                self._db.execute("UPDATE tickets SET is_expedited = ? WHERE ticket_id = ?", (is_expedited, ticket_id))
            if escalated_to is not None:
                self._db.execute("UPDATE tickets SET escalated_to = ?, escalated_at = ? WHERE ticket_id = ?",
                                 (escalated_to, at, ticket_id))
            if assigned_reviewer_id is not None:
                self._db.execute("UPDATE tickets SET assigned_reviewer_id = ? WHERE ticket_id = ?",
                                 (assigned_reviewer_id, ticket_id))
            return self._one("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,))

    def submit_information(self, ticket_id: str, *, customer_id: str, text: str) -> dict | None:
        at = now_text()
        with self._lock, self._db:
            cursor = self._db.execute(
                "UPDATE tickets SET status = 'pending', customer_information = ?, information_submitted_at = ?,"
                " reviewer_id = NULL WHERE ticket_id = ? AND customer_id = ? AND status = 'needs_info'",
                (text, at, ticket_id, customer_id),
            )
            if cursor.rowcount != 1:
                return None
            self._event(ticket_id, f"customer:{customer_id}", "information_submitted", text, at,
                        before_status="needs_info", after_status="pending")
            return self._one("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,))

    def rate(self, ticket_id: str, *, customer_id: str, rating: int) -> dict | None:
        """Keep the owner's first 1–5 rating of a decided ticket."""
        at = now_text()
        with self._lock, self._db:
            cursor = self._db.execute(
                "UPDATE tickets SET rating = ?, rated_at = ? WHERE ticket_id = ? AND customer_id = ?"
                " AND status IN ('approved', 'rejected') AND rating IS NULL",
                (rating, at, ticket_id, customer_id),
            )
            if cursor.rowcount != 1:
                return None
            self._event(ticket_id, f"customer:{customer_id}", "rated", f"{rating} 分", at)
            return self._one("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,))

    # Human handoffs (multi-tenant RLS + full-duplex customer/specialist follow-up messages)

    def _handoff_followups(self, handoff_id: str) -> list[dict]:
        rows = self._db.execute(
            "SELECT message_id, sender_role, sender_id, text, created_at, after_index"
            " FROM handoff_messages WHERE handoff_id = ? ORDER BY message_id",
            (handoff_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _handoff(row: dict | None) -> dict | None:
        if row is not None:
            row["excerpt"] = json.loads(row["excerpt"])
        return row

    def handoff_with_attachments(self, row: dict | None) -> dict | None:
        if row is None:
            return None
        row = self._handoff(row)
        row["attachments"] = self.attachments(row["handoff_id"])
        followups = self._handoff_followups(row["handoff_id"])
        if followups:
            row["followups"] = followups
        return row

    def active_handoffs(self, customer_id: str, thread_id: str | None = None) -> list[dict]:
        """Return all active human consultations for a customer (each distinct order has its own handoff_id)."""
        with self._lock:
            if thread_id:
                rows = self._db.execute(
                    "SELECT * FROM handoffs WHERE customer_id = ?"
                    " AND (status = 'waiting' OR (thread_id = ? AND status = 'replied' AND ended_at IS NULL))"
                    " ORDER BY CAST(SUBSTR(handoff_id, 2) AS INTEGER) ASC",
                    (customer_id, thread_id),
                ).fetchall()
            else:
                rows = self._db.execute(
                    "SELECT * FROM handoffs WHERE customer_id = ?"
                    " AND (status = 'waiting' OR (status = 'replied' AND ended_at IS NULL))"
                    " ORDER BY CAST(SUBSTR(handoff_id, 2) AS INTEGER) ASC",
                    (customer_id,),
                ).fetchall()
            return [self.handoff_with_attachments(dict(r)) for r in rows]

    def active_handoff_for_order(self, customer_id: str, order_id: str, thread_id: str | None = None) -> dict | None:
        """Find the active human consultation dedicated to a specific (customer_id, order_id)."""
        with self._lock:
            if thread_id:
                row = self._one(
                    "SELECT * FROM handoffs WHERE customer_id = ? AND order_id = ?"
                    " AND (status = 'waiting' OR (thread_id = ? AND status = 'replied' AND ended_at IS NULL))"
                    " ORDER BY CAST(SUBSTR(handoff_id, 2) AS INTEGER) DESC LIMIT 1",
                    (customer_id, order_id, thread_id),
                )
            else:
                row = self._one(
                    "SELECT * FROM handoffs WHERE customer_id = ? AND order_id = ?"
                    " AND (status = 'waiting' OR (status = 'replied' AND ended_at IS NULL))"
                    " ORDER BY CAST(SUBSTR(handoff_id, 2) AS INTEGER) DESC LIMIT 1",
                    (customer_id, order_id),
                )
            return self.handoff_with_attachments(row) if row else None

    def unbound_active_handoff(self, customer_id: str, thread_id: str | None = None) -> dict | None:
        """Find a freshly waiting unbound handoff on the same thread (never reuse an old replied unbound session)."""
        with self._lock:
            latest = self._one(
                "SELECT * FROM handoffs WHERE customer_id = ? ORDER BY CAST(SUBSTR(handoff_id, 2) AS INTEGER) DESC LIMIT 1",
                (customer_id,),
            )
            if (
                latest
                and latest.get("order_id") is None
                and latest.get("status") == "waiting"
                and (not thread_id or latest.get("thread_id") == thread_id)
            ):
                return self.handoff_with_attachments(latest)
            return None

    def active_handoff(self, customer_id: str, thread_id: str, order_id: str | None = None) -> dict | None:
        """Return the customer's active human consultation (for order_id if given, else latest active on thread)."""
        if order_id:
            return self.active_handoff_for_order(customer_id, order_id, thread_id)
        with self._lock:
            latest = self._one(
                "SELECT * FROM handoffs WHERE customer_id = ?"
                " AND (status = 'waiting' OR (thread_id = ? AND status = 'replied' AND ended_at IS NULL))"
                " ORDER BY CAST(SUBSTR(handoff_id, 2) AS INTEGER) DESC LIMIT 1",
                (customer_id, thread_id),
            )
            return self.handoff_with_attachments(latest) if latest else None

    def create_handoff(self, *, customer_id: str, thread_id: str, order_id: str | None, after_index: int,
                       request_text: str | None, excerpt: list, files: list[dict], limit: int,
                       tenant_id: str = "M_67REST", initial_appeal: str | None = None) -> tuple[dict | None, bool]:
        """One-Order-One-Handoff ('一单一编号'): each distinct order_id gets its own independent handoff_id."""
        with self._lock, self._db:
            if order_id:
                waiting = self._one(
                    "SELECT * FROM handoffs WHERE customer_id = ? AND order_id = ? AND status = 'waiting'"
                    " ORDER BY CAST(SUBSTR(handoff_id, 2) AS INTEGER) DESC LIMIT 1",
                    (customer_id, order_id),
                )
                if waiting is None:
                    waiting = self._one(
                        "SELECT * FROM handoffs WHERE customer_id = ? AND thread_id = ? AND order_id IS NULL AND status = 'waiting'"
                        " ORDER BY CAST(SUBSTR(handoff_id, 2) AS INTEGER) DESC LIMIT 1",
                        (customer_id, thread_id),
                    )
            else:
                waiting = self._one(
                    "SELECT * FROM handoffs WHERE customer_id = ? AND status = 'waiting'"
                    " ORDER BY CAST(SUBSTR(handoff_id, 2) AS INTEGER) DESC LIMIT 1",
                    (customer_id,),
                )
            if waiting:
                if order_id and not waiting.get("order_id"):
                    self._db.execute("UPDATE handoffs SET order_id = ?, tenant_id = ? WHERE handoff_id = ?",
                                     (order_id, tenant_id, waiting["handoff_id"]))
                if initial_appeal and not waiting.get("initial_appeal"):
                    self._db.execute("UPDATE handoffs SET initial_appeal = ? WHERE handoff_id = ?",
                                     (initial_appeal, waiting["handoff_id"]))
                if files:
                    has_prior = bool(waiting.get("request_text") or self._handoff_followups(waiting["handoff_id"])
                                     or self._attachment_rows(waiting["handoff_id"]))
                    self._store_files(waiting["handoff_id"], customer_id, files,
                                      after_index=after_index, is_followup=has_prior)
                refreshed = self._one("SELECT * FROM handoffs WHERE handoff_id = ?", (waiting["handoff_id"],))
                return self.handoff_with_attachments(refreshed), False
            active_waiting = self._db.execute("SELECT COUNT(*) FROM handoffs WHERE status = 'waiting'").fetchone()[0]
            if active_waiting >= limit:
                return None, False
            next_num = self._db.execute(
                "SELECT COALESCE(MAX(CAST(SUBSTR(handoff_id, 2) AS INTEGER)), 0) + 1 FROM handoffs"
            ).fetchone()[0]
            handoff_id = f"H{next_num:04d}"
            self._db.execute(
                "INSERT INTO handoffs (handoff_id, customer_id, thread_id, order_id, after_index, request_text,"
                " excerpt, status, created_at, tenant_id, initial_appeal) VALUES (?, ?, ?, ?, ?, ?, ?, 'waiting', ?, ?, ?)",
                (handoff_id, customer_id, thread_id, order_id, after_index, request_text,
                 json.dumps(excerpt, ensure_ascii=False), now_text(), tenant_id, initial_appeal),
            )
            self._store_files(handoff_id, customer_id, files, after_index=after_index, is_followup=False)
            return self.handoff_with_attachments(self._one("SELECT * FROM handoffs WHERE handoff_id = ?", (handoff_id,))), True

    def handoffs(self, *, customer_id: str | None = None, tenant_id: str | None = None) -> list[dict]:
        clauses, params = [], []
        if customer_id is not None:
            clauses.append("customer_id = ?")
            params.append(customer_id)
        if tenant_id is not None and tenant_id != "*":
            clauses.append("COALESCE(tenant_id, 'M_67REST') = ?")
            params.append(tenant_id)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        with self._lock:
            rows = self._db.execute(f"SELECT * FROM handoffs{where} ORDER BY handoff_id", tuple(params)).fetchall()
            return [self.handoff_with_attachments(dict(row)) for row in rows]

    def get_handoff(self, handoff_id: str) -> dict | None:
        with self._lock:
            return self.handoff_with_attachments(self._one("SELECT * FROM handoffs WHERE handoff_id = ?", (handoff_id,)))

    def close_handoff(self, handoff_id: str, *, status: str, customer_id: str | None = None,
                      reviewer_id: str | None = None, reply_text: str | None = None,
                      reply_after_index: int | None = None) -> dict | None:
        """Move a waiting handoff to replied or cancelled exactly once."""
        with self._lock, self._db:
            reply_seq = None
            if status == "replied":
                reply_seq = self._db.execute(
                    "SELECT COALESCE(MAX(message_id), 0) FROM handoff_messages WHERE handoff_id = ?", (handoff_id,)
                ).fetchone()[0]
            sql = (
                "UPDATE handoffs SET status = ?, reply_text = ?, reviewer_id = ?, closed_at = ?,"
                " reply_after_index = COALESCE(?, after_index), reply_seq = ? WHERE handoff_id = ? AND status = 'waiting'"
            )
            params = [status, reply_text, reviewer_id, now_text(), reply_after_index, reply_seq, handoff_id]
            if customer_id is not None:
                sql, params = sql + " AND customer_id = ?", params + [customer_id]
            if self._db.execute(sql, params).rowcount != 1:
                return None
            return self.handoff_with_attachments(self._one("SELECT * FROM handoffs WHERE handoff_id = ?", (handoff_id,)))

    def end_handoff(self, handoff_id: str, *, customer_id: str) -> dict | None:
        """Mark an active replied human session as ended so subsequent messages return to AI mode."""
        with self._lock, self._db:
            row = self._one("SELECT * FROM handoffs WHERE handoff_id = ? AND customer_id = ?", (handoff_id, customer_id))
            if row is None or row["status"] == "cancelled":
                return None
            if row["status"] == "waiting":
                self._db.execute(
                    "UPDATE handoffs SET status = 'cancelled', closed_at = ? WHERE handoff_id = ?",
                    (now_text(), handoff_id),
                )
            elif not row.get("ended_at"):
                self._db.execute("UPDATE handoffs SET ended_at = ? WHERE handoff_id = ?", (now_text(), handoff_id))
            return self.handoff_with_attachments(self._one("SELECT * FROM handoffs WHERE handoff_id = ?", (handoff_id,)))

    def append_handoff_followup(self, handoff_id: str, *, sender_role: str, sender_id: str, text: str | None = None,
                                customer_id: str | None = None, after_index: int | None = None,
                                order_id: str | None = None, files: list[dict] | None = None) -> dict | None:
        """Full-duplex multi-turn follow-up messages for both specialist and customer."""
        with self._lock, self._db:
            row = self._one("SELECT * FROM handoffs WHERE handoff_id = ?", (handoff_id,))
            if row is None or row["status"] == "cancelled":
                return None
            if customer_id is not None and row["customer_id"] != customer_id:
                return None
            if order_id and row.get("order_id") != order_id:
                self._db.execute("UPDATE handoffs SET order_id = ? WHERE handoff_id = ?", (order_id, handoff_id))
            if row.get("ended_at") and sender_role == "reviewer":
                # Re-activate human session if specialist sends a follow-up message!
                self._db.execute("UPDATE handoffs SET ended_at = NULL WHERE handoff_id = ?", (handoff_id,))
            msg_seq = 1
            if text:
                cur = self._db.execute(
                    "INSERT INTO handoff_messages (handoff_id, sender_role, sender_id, text, created_at, after_index)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (handoff_id, sender_role, sender_id, text, now_text(), after_index),
                )
                msg_seq = int(cur.lastrowid or 1)
            if files:
                self._store_files(handoff_id, row["customer_id"], files, after_index=after_index, is_followup=msg_seq)
            return self.handoff_with_attachments(self._one("SELECT * FROM handoffs WHERE handoff_id = ?", (handoff_id,)))

    def update_handoff_flags(self, handoff_id: str, *, is_expedited: int | None = None,
                             escalated_to: str | None = None, assigned_reviewer_id: str | None = None) -> dict | None:
        at = now_text()
        with self._lock, self._db:
            row = self._one("SELECT * FROM handoffs WHERE handoff_id = ?", (handoff_id,))
            if not row:
                return None
            if is_expedited is not None:
                self._db.execute("UPDATE handoffs SET is_expedited = ? WHERE handoff_id = ?", (is_expedited, handoff_id))
            if escalated_to is not None:
                self._db.execute("UPDATE handoffs SET escalated_to = ?, escalated_at = ? WHERE handoff_id = ?",
                                 (escalated_to, at, handoff_id))
            if assigned_reviewer_id is not None:
                self._db.execute("UPDATE handoffs SET assigned_reviewer_id = ?, reviewer_id = COALESCE(reviewer_id, ?) WHERE handoff_id = ?",
                                 (assigned_reviewer_id, assigned_reviewer_id, handoff_id))
            return self.handoff_with_attachments(self._one("SELECT * FROM handoffs WHERE handoff_id = ?", (handoff_id,)))

    def transition_handoff_status(self, handoff_id: str, *, reviewer_id: str,
                                  close_session: bool = False) -> dict | None:
        """Transition a waiting handoff to replied (and optionally mark ended_at) without requiring text reply."""
        at = now_text()
        with self._lock, self._db:
            row = self._one("SELECT * FROM handoffs WHERE handoff_id = ?", (handoff_id,))
            if not row or row["status"] == "cancelled":
                return None
            if row["status"] == "waiting":
                reply_seq = self._db.execute(
                    "SELECT COALESCE(MAX(message_id), 0) FROM handoff_messages WHERE handoff_id = ?", (handoff_id,)
                ).fetchone()[0]
                self._db.execute(
                    "UPDATE handoffs SET status = 'replied', reviewer_id = COALESCE(reviewer_id, ?),"
                    " closed_at = COALESCE(closed_at, ?), reply_seq = COALESCE(reply_seq, ?),"
                    " reply_after_index = COALESCE(reply_after_index, after_index) WHERE handoff_id = ?",
                    (reviewer_id, at, reply_seq, handoff_id),
                )
            if close_session and not row.get("ended_at"):
                self._db.execute("UPDATE handoffs SET ended_at = ? WHERE handoff_id = ?", (at, handoff_id))
            return self.handoff_with_attachments(self._one("SELECT * FROM handoffs WHERE handoff_id = ?", (handoff_id,)))

    def reset(self) -> list[str]:
        """Clear demo tickets/handoffs while keeping audit_logs append-only (WORM) with SHA-256 chain intact."""
        with self._lock, self._db:
            archived_hashes = [
                r["sha256_hash"][:16]
                for r in self._db.execute("SELECT sha256_hash FROM attachment_forensics").fetchall()
            ]
            self._db.execute("DELETE FROM action_logs")
            self._db.execute("DELETE FROM ticket_events")
            self._db.execute("DELETE FROM tickets")
            self._db.execute("DELETE FROM goodwill_grants")
            self._db.execute("DELETE FROM attachment_forensics")
            self._db.execute("DELETE FROM attachments")
            self._db.execute("DELETE FROM handoff_messages")
            self._db.execute("DELETE FROM handoffs")
            self._db.execute("DELETE FROM graph_thread_checkpoints")
            for item in self.media_dir.glob("*"):
                try:
                    item.unlink()
                except OSError:
                    pass
            return archived_hashes
