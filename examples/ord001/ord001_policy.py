"""Load and apply the versioned compensation rule and T1/T2 subrogation actuarial model for ORD001."""

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


def _parse_local_seconds(raw: str | None) -> int | None:
    if not raw or not isinstance(raw, str):
        return None
    parsed = time.fromisoformat(raw)
    if parsed.tzinfo is not None:
        raise ValueError("The exercise uses local times without timezone offsets")
    return int((datetime.combine(date.min, parsed) - datetime.combine(date.min, time.min)).total_seconds())


def measure_order(order: dict[str, str] | None) -> dict:
    if order is None:
        return {"status": "not_found", "reason_code": "order_not_found", "message": "查不到这笔模拟订单。"}

    delivery_status = order.get("status")
    if not delivery_status:
        return {"status": "needs_info", "reason_code": "missing_delivery_status", "message": "缺少订单送达状态。"}
    if delivery_status != "delivered":
        return {"status": "ineligible", "reason_code": "not_delivered", "message": "本流程处理已送达订单。"}

    try:
        expected_sec = _parse_local_seconds(order.get("expected_at"))
        delivered_sec = _parse_local_seconds(order.get("delivered_at"))
        if expected_sec is None or delivered_sec is None:
            raise ValueError("Missing delivery timestamps")
        late_seconds = delivered_sec - expected_sec
        # Support cross-midnight late-night orders (e.g., expected 23:50, delivered 00:35 next day -> +45 min).
        if late_seconds < -12 * 3600:
            late_seconds += 86400
    except (TypeError, ValueError):
        return {"status": "needs_info", "reason_code": "invalid_delivery_times", "message": "配送时间不完整，暂时无法判断。"}

    return {"late_seconds": late_seconds, "late_minutes": int(late_seconds / 60)}


def policy_outcome(facts: dict, policy: CompensationPolicy, *, eligible: bool, amount_yuan: float | None = None) -> dict:
    outcome = {**facts, "policy_version": policy.version}
    if eligible:
        minutes, seconds = divmod(facts["late_seconds"], 60)
        delay = f"{minutes} 分钟 {seconds} 秒" if seconds else f"{minutes} 分钟"
        proposed = policy.coupon_yuan
        return {
            **outcome,
            "status": "pending",
            "reason_code": "eligible_for_review",
            "proposed_coupon_yuan": proposed,
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
    raw_amt = order.get("amount_yuan") if isinstance(order, dict) else None
    amt_val = float(raw_amt) if isinstance(raw_amt, (int, float)) else None
    return policy_outcome(facts, policy, eligible=eligible, amount_yuan=amt_val)


def compute_actuarial_subrogation(order: dict | None, policy: CompensationPolicy | None = None) -> dict:
    """Compute T1 (merchant prep) vs. T2 (platform logistics) cost split, margin cap, and STP tier."""
    policy = policy or load_policy()
    if not order:
        return {"stp_tier": "NONE", "cost_bearer": "none", "merchant_bear_yuan": 0.0, "platform_bear_yuan": 0.0}

    decision = evaluate_order(
        {"status": order.get("status"), "expected_at": order.get("expected_at"), "delivered_at": order.get("delivered_at")},
        policy,
    )
    amount = float(order.get("amount_yuan") or 0)
    coupon = float(policy.coupon_yuan)
    margin_cap_yuan = round(max(2.0, amount * 0.40), 1) if amount > 0 else coupon

    try:
        prep_prom = _parse_local_seconds(order.get("prep_promised_at"))
        prep_done = _parse_local_seconds(order.get("prep_done_at"))
        t1_late_sec = max(0, (prep_done - prep_prom) if (prep_prom is not None and prep_done is not None) else 0)
    except ValueError:
        t1_late_sec = 0

    late_sec = decision.get("late_seconds")
    if decision["status"] == "needs_info":
        return {
            "stp_tier": "YELLOW_VERIFY",
            "stp_note": "弱网签收时间戳待核验 · 建议调取 GPS 电子围栏或顾客截图确认",
            "cost_bearer": "platform_pool",
            "merchant_bear_yuan": 0.0,
            "platform_bear_yuan": 0.0,
            "t1_merchant_late_min": round(t1_late_sec / 60, 1),
            "rider_sla_extended_min": round(t1_late_sec / 60),
            "goodwill_care_yuan": 0,
            "margin_cap_yuan": margin_cap_yuan,
        }

    if decision["status"] != "pending":
        raw_gw = round(min(3.0, margin_cap_yuan), 1)
        goodwill = int(raw_gw) if raw_gw == int(raw_gw) else raw_gw
        goodwill = goodwill if (isinstance(late_sec, int) and 900 <= late_sec <= policy.threshold_minutes * 60) else 0
        return {
            "stp_tier": "CARE_GOODWILL" if goodwill else "INELIGIBLE_EXEMPT",
            "stp_note": (
                f"临界延迟柔性关怀区：主规则免责（商家 ¥0 承担），平台体验金可提供 ¥{goodwill} 暖心安抚"
                if goodwill else "准时保容差免责区：商家与骑手均 0 责任"
            ),
            "cost_bearer": "platform_pool" if goodwill else "none",
            "merchant_bear_yuan": 0.0,
            "platform_bear_yuan": float(goodwill),
            "t1_merchant_late_min": round(t1_late_sec / 60, 1),
            "rider_sla_extended_min": round(t1_late_sec / 60),
            "goodwill_care_yuan": goodwill,
            "margin_cap_yuan": margin_cap_yuan,
        }

    # Eligible order (late_seconds > threshold): cap TOTAL payout at min(coupon, margin_cap_yuan) so low-AOV orders never drain platform pool!
    effective_coupon = round(min(coupon, margin_cap_yuan), 1)
    total_late = max(1, int(late_sec or 1))
    if t1_late_sec <= 0:
        return {
            "stp_tier": "STP_L1_GREEN",
            "stp_note": f"绿灯直通级：餐厅准时/提前出餐，纯运力延误，平台准时保池 100% 出资 ¥{effective_coupon}（本店 ¥0 承担）",
            "cost_bearer": "platform_pool",
            "effective_coupon_yuan": effective_coupon,
            "merchant_bear_yuan": 0.0,
            "platform_bear_yuan": effective_coupon,
            "t1_merchant_late_min": 0.0,
            "rider_sla_extended_min": 0,
            "goodwill_care_yuan": 0,
            "margin_cap_yuan": margin_cap_yuan,
        }

    merchant_ratio = min(1.0, t1_late_sec / total_late)
    merchant_share = round(min(effective_coupon * merchant_ratio, margin_cap_yuan), 1)
    platform_share = round(max(0.0, effective_coupon - merchant_share), 1)
    return {
        "stp_tier": "STP_L2_SHARED",
        "stp_note": (
            f"餐骑共担清分级：出餐晚 {round(t1_late_sec / 60)} 分钟（本店承担 ¥{merchant_share}）"
            f" + 运力通行延误（平台准时保池承担 ¥{platform_share}）"
        ),
        "cost_bearer": "shared_subrogation",
        "effective_coupon_yuan": effective_coupon,
        "merchant_bear_yuan": merchant_share,
        "platform_bear_yuan": platform_share,
        "t1_merchant_late_min": round(t1_late_sec / 60, 1),
        "rider_sla_extended_min": round(t1_late_sec / 60),
        "goodwill_care_yuan": 0,
        "margin_cap_yuan": margin_cap_yuan,
    }
