"""Customer-facing wording for the ORD001 web demo. Times and amounts come from the caller."""

from ord001_web_store import STATUS_TEXT

NOT_VERIFIED = "未找到这笔订单，请核对订单号，或从「我的订单」中选择。"
QUERY_FAILED = "订单查询失败，请重试。"
CANCELLED = "已取消提交。"


def delay_text(late_seconds: int) -> str:
    if late_seconds <= 0:
        return "没有晚到"
    minutes, seconds = divmod(late_seconds, 60)
    return f"晚到 {minutes} 分钟 {seconds} 秒" if seconds else f"晚到 {minutes} 分钟"


def threshold_text(policy) -> str:
    minutes = policy.threshold_minutes
    return f"晚到 {minutes} 分钟及以上" if policy.include_threshold else f"晚到超过 {minutes} 分钟"


def confirm_text(claim: dict) -> str:
    return (
        f"{claim['order_id']} {delay_text(claim['late_seconds'])}。"
        f"可申请 ¥{claim['proposed_coupon_yuan']} 补偿券，确认后提交审核。"
    )


def outcome_text(order: dict, decision: dict, policy) -> str:
    """Explain an evaluate_order result that cannot be submitted."""
    reason = decision["reason_code"]
    if reason == "delay_below_threshold":
        return (
            f"{order['order_id']} {delay_text(decision['late_seconds'])}。"
            f"需{threshold_text(policy)}才能申请。"
        )
    if reason == "not_delivered":
        return f"订单 {order['order_id']} 尚未送达，请在送达后申请。"
    return f"订单 {order['order_id']} 暂缺送达记录，无法提交申请。"


def ticket_text(ticket: dict, *, created: bool) -> str:
    status = ticket["status"]
    if created:
        head = f"申请 {ticket['ticket_id']} 已提交，待审核。"
    else:
        head = f"订单 {ticket['order_id']} 的申请 {ticket['ticket_id']}：{STATUS_TEXT[status]}。"
    if status == "needs_info" and ticket.get("information_request"):
        return head + f"请补充：{ticket['information_request']}"
    if status == "approved":
        return head + f"¥{ticket['coupon_issued_yuan']} 补偿券已发放。"
    if status == "rejected" and ticket["review_note"]:
        return head + f"原因：{ticket['review_note']}"
    return head
