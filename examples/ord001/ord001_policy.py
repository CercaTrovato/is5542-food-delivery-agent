"""Load and apply the versioned compensation rule for the ORD001 exercise."""

import json
import os
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path


@dataclass(frozen=True)
class CompensationPolicy:
    version: str
    threshold_minutes: int
    include_threshold: bool
    coupon_yuan: int


def load_policy() -> CompensationPolicy:
    configured_path = os.getenv("ORD001_POLICY_PATH")
    path = Path(configured_path) if configured_path else Path(__file__).with_name("demo-policy.json")
    policy = CompensationPolicy(**json.loads(path.read_text(encoding="utf-8")))
    if (
        not isinstance(policy.version, str)
        or not policy.version.strip()
        or type(policy.threshold_minutes) is not int
        or policy.threshold_minutes < 0
        or type(policy.include_threshold) is not bool
        or type(policy.coupon_yuan) is not int
        or policy.coupon_yuan <= 0
    ):
        raise ValueError(f"Invalid compensation policy: {path}")
    return policy


def measure_order(order: dict[str, str] | None) -> dict:
    if order is None:
        return {"status": "not_found", "reason_code": "order_not_found", "message": "查不到这笔模拟订单。"}

    delivery_status = order.get("status")
    if not delivery_status:
        return {"status": "needs_info", "reason_code": "missing_delivery_status", "message": "缺少订单送达状态。"}
    if delivery_status != "delivered":
        return {"status": "ineligible", "reason_code": "not_delivered", "message": "本流程处理已送达订单。"}

    try:
        expected = time.fromisoformat(order.get("expected_at", ""))
        delivered = time.fromisoformat(order.get("delivered_at", ""))
        if expected.tzinfo is not None or delivered.tzinfo is not None:
            raise ValueError("The exercise uses local same-day times")
        late_seconds = int((
            datetime.combine(date.min, delivered) - datetime.combine(date.min, expected)
        ).total_seconds())
    except (TypeError, ValueError):
        return {"status": "needs_info", "reason_code": "invalid_delivery_times", "message": "配送时间不完整，暂时无法判断。"}

    return {"late_seconds": late_seconds, "late_minutes": int(late_seconds / 60)}


def policy_outcome(facts: dict, policy: CompensationPolicy, *, eligible: bool) -> dict:
    outcome = {**facts, "policy_version": policy.version}
    if eligible:
        minutes, seconds = divmod(facts["late_seconds"], 60)
        delay = f"{minutes} 分钟 {seconds} 秒" if seconds else f"{minutes} 分钟"
        return {
            **outcome,
            "status": "pending",
            "reason_code": "eligible_for_review",
            "proposed_coupon_yuan": policy.coupon_yuan,
            "message": f"订单晚到 {delay}，符合申请条件。请确认是否提交。",
        }
    return {
        **outcome,
        "status": "ineligible",
        "reason_code": "delay_below_threshold",
        "message": "订单未达到本次补偿条件。",
    }


def evaluate_order(order: dict[str, str] | None, policy: CompensationPolicy | None = None) -> dict:
    policy = policy or load_policy()
    facts = measure_order(order)
    if "status" in facts:
        return {**facts, "policy_version": policy.version}

    late_seconds = facts["late_seconds"]
    threshold_seconds = policy.threshold_minutes * 60
    eligible = late_seconds >= threshold_seconds if policy.include_threshold else late_seconds > threshold_seconds
    return policy_outcome(facts, policy, eligible=eligible)
