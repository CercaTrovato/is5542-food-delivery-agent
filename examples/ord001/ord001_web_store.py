"""Mock accounts, orders and the ticket store behind the ORD001 web demo."""

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

DATA_PATH = Path(__file__).with_name("demo-data.json")
# evaluate_order only receives these order facts.
ORDER_FACT_KEYS = ("status", "expected_at", "delivered_at")
DECISION_STATUS = {"approve": "approved", "reject": "rejected", "request_info": "needs_info"}
STATUS_TEXT = {"pending": "待审核", "needs_info": "待补充", "approved": "已批准", "rejected": "已驳回"}

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
    UNIQUE (order_id, policy_version)
);
CREATE TABLE IF NOT EXISTS ticket_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id TEXT NOT NULL,
    at TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    note TEXT
);
"""


def now_text() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def normalize_order_id(raw: str) -> str:
    return str(raw).strip().upper()


def order_facts(order: dict) -> dict:
    return {key: order.get(key) for key in ORDER_FACT_KEYS}


class DemoData:
    """Mock customers, reviewers and same-day orders from demo-data.json."""

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
    """SQLite tickets. The same order under the same policy version keeps one ticket."""

    def __init__(self, path: str = ":memory:"):
        self._lock = threading.Lock()
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._migrate()
        self._db.executescript(SCHEMA)

    def _migrate(self) -> None:
        """Replace the original three-state table atomically, preserving tickets and events."""
        table = self._db.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'tickets'").fetchone()
        if table is None:
            return
        columns = {row["name"] for row in self._db.execute("PRAGMA table_info(tickets)")}
        if "needs_info" in table["sql"] and {"information_request", "customer_information",
                                                "information_requested_at", "information_submitted_at"} <= columns:
            return
        ticket_schema = SCHEMA.split("CREATE TABLE IF NOT EXISTS ticket_events", 1)[0]
        with self._db:
            self._db.execute("BEGIN IMMEDIATE")
            self._db.execute(ticket_schema.replace("IF NOT EXISTS tickets", "tickets_upgrade", 1))
            target = [row["name"] for row in self._db.execute("PRAGMA table_info(tickets_upgrade)")]
            common = ", ".join(f'"{name}"' for name in target if name in columns)
            self._db.execute(f"INSERT INTO tickets_upgrade ({common}) SELECT {common} FROM tickets")
            self._db.execute("DROP TABLE tickets")
            self._db.execute("ALTER TABLE tickets_upgrade RENAME TO tickets")

    def close(self) -> None:
        with self._lock:
            self._db.close()

    def _one(self, sql: str, params: tuple) -> dict | None:
        row = self._db.execute(sql, params).fetchone()
        return dict(row) if row else None

    def _event(self, ticket_id: str, actor: str, action: str, note: str | None, at: str) -> None:
        self._db.execute(
            "INSERT INTO ticket_events (ticket_id, at, actor, action, note) VALUES (?, ?, ?, ?, ?)",
            (ticket_id, at, actor, action, note),
        )

    def get(self, ticket_id: str) -> dict | None:
        with self._lock:
            return self._one("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,))

    def find(self, order_id: str, policy_version: str) -> dict | None:
        with self._lock:
            return self._one(
                "SELECT * FROM tickets WHERE order_id = ? AND policy_version = ?", (order_id, policy_version)
            )

    def tickets(self, *, customer_id: str | None = None) -> list[dict]:
        sql, params = "SELECT * FROM tickets", ()
        if customer_id is not None:
            sql, params = sql + " WHERE customer_id = ?", (customer_id,)
        with self._lock:
            return [dict(row) for row in self._db.execute(sql + " ORDER BY ticket_id", params).fetchall()]

    def events(self, ticket_id: str) -> list[dict]:
        with self._lock:
            rows = self._db.execute(
                "SELECT at, actor, action, note FROM ticket_events WHERE ticket_id = ? ORDER BY event_id",
                (ticket_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def create_or_get(self, *, customer_id: str, order: dict, decision: dict) -> tuple[dict, bool]:
        """Create a pending ticket, or return the one already kept for this order and policy version."""
        key = (order["order_id"], decision["policy_version"])
        with self._lock, self._db:
            existing = self._one("SELECT * FROM tickets WHERE order_id = ? AND policy_version = ?", key)
            if existing:
                return existing, False
            ticket_id = f"T{self._db.execute('SELECT COUNT(*) FROM tickets').fetchone()[0] + 1:04d}"
            created_at = now_text()
            self._db.execute(
                "INSERT INTO tickets (ticket_id, customer_id, order_id, policy_version, expected_at, delivered_at,"
                " late_seconds, proposed_coupon_yuan, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)",
                (ticket_id, customer_id, *key, order["expected_at"], order["delivered_at"],
                 decision["late_seconds"], decision["proposed_coupon_yuan"], created_at),
            )
            self._event(ticket_id, f"customer:{customer_id}", "submitted", None, created_at)
            return self._one("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)), True

    def decide(self, ticket_id: str, *, decision: str, reviewer_id: str, note: str | None) -> dict | None:
        """Act on a pending ticket once; asking for information is not a final decision."""
        status = DECISION_STATUS[decision]
        at = now_text()
        with self._lock, self._db:
            if status == "needs_info":
                cursor = self._db.execute(
                    "UPDATE tickets SET status = 'needs_info', reviewer_id = ?, information_request = ?,"
                    " information_requested_at = ?, customer_information = NULL, information_submitted_at = NULL,"
                    " decided_at = NULL, review_note = NULL, coupon_issued_yuan = NULL"
                    " WHERE ticket_id = ? AND status = 'pending'",
                    (reviewer_id, note, at, ticket_id),
                )
                action = "information_requested"
            else:
                # Approval records the mock coupon as issued. The exercise moves no real money.
                cursor = self._db.execute(
                    "UPDATE tickets SET status = ?, decided_at = ?, reviewer_id = ?, review_note = ?,"
                    " coupon_issued_yuan = CASE WHEN ? = 'approved' THEN proposed_coupon_yuan END"
                    " WHERE ticket_id = ? AND status = 'pending'",
                    (status, at, reviewer_id, note, status, ticket_id),
                )
                action = status
            if cursor.rowcount != 1:
                return None
            self._event(ticket_id, f"reviewer:{reviewer_id}", action, note, at)
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
            self._event(ticket_id, f"customer:{customer_id}", "information_submitted", text, at)
            return self._one("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,))

    def reset(self) -> None:
        with self._lock, self._db:
            self._db.execute("DELETE FROM ticket_events")
            self._db.execute("DELETE FROM tickets")
