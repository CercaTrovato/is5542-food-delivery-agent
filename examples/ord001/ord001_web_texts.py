"""Customer-facing wording for the ORD001 web demo. Times and amounts come from the caller."""

from ord001_web_store import STATUS_TEXT

NOT_VERIFIED = "未找到这笔订单，请核对订单号，或从「我的订单」中选择。"
QUERY_FAILED = "订单查询失败，请重试。"
CANCELLED = "已取消提交。"
# Replaces a model reply that promised money or results the server has not decided.
GUARDED_REPLY = "抱歉，这一点我不能直接答复或承诺。补偿资格和金额以系统核实、商家审核为准；需要的话可以点上方「转人工」。"


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
        f"实在抱歉让您久等了！经核实，{claim['order_id']} {delay_text(claim['late_seconds'])}。"
        f"可申请 ¥{claim['proposed_coupon_yuan']} 无门槛补偿券，确认后提交审核。"
    )


def outcome_text(order: dict, decision: dict, policy) -> str:
    """Explain an evaluate_order result with genuine warmth while preserving exact verified timestamps."""
    reason = decision["reason_code"]
    if reason == "delay_below_threshold":
        late_sec = decision.get("late_seconds", 0)
        core = (
            f"非常抱歉让您久等了！经核实，{order['order_id']} 预计 {order['expected_at']}，实际 {order['delivered_at']}，"
            f"{delay_text(late_sec)}。需{threshold_text(policy)}才能申请。"
        )
        if late_sec >= 900:
            return core + "距离起赔线仅差一点，您可在右侧进度卡一键秒领 ¥3 准时保暖心券，或点上方「转人工」跟进安抚。"
        return core + "感谢您在高峰期的理解与体谅。"
    if reason == "not_delivered":
        return (
            f"订单 {order['order_id']} 正在正常时效内为您加急配送，尚未送达；"
            "系统已自动开启准时保静默守护，送达后若达到晚到条件可立即申请补偿。"
        )
    return (
        f"非常抱歉！订单 {order['order_id']} 已完成交付，因楼宇弱网暂缺签收时间记录，无法自动核算延误；"
        "可点下方「相册」上传截图或点上方「转人工」结合电子围栏轨迹为您核实。"
    )


def ticket_text(ticket: dict, *, created: bool) -> str:
    status = ticket["status"]
    if created:
        if status == "approved":
            return f"申请 {ticket['ticket_id']} 已通过准时保直通审核，¥{ticket['coupon_issued_yuan']} 补偿券已发放。"
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
