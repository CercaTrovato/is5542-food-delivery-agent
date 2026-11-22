"use strict";

const TABS = ["pending", "decided", "handoffs"];
const HANDOFF_STATUS = { waiting: "待回复", replied: "已回复", ended: "已结束", cancelled: "顾客已取消" };
const TICKET_STATE_LABELS = { pending: "待审核", needs_info: "待补充", approved: "已通过", rejected: "已驳回", ended: "已结束", waiting: "待回复", replied: "已回复" };
const LINE_ROLE = { customer: "顾客", assistant: "AI", tool: "查询" };
const BASE_TITLE = "配送关怀 · 67餐厅核损工作台";
const drafts = new Map();
const replyDrafts = new Map();
const followupDrafts = new Map();
const actionNoteDrafts = new Map();
const actionAmountDrafts = new Map();
const expandedFollowups = new Set();
let signedIn = false;
let currentReviewer = null;
let allReviewers = [];
let busy = false;
let lastTickets = "";
let selectedTab = "pending";
let pendingCountSnapshot = 0;
let pendingConfirmAction = null;

function canHandle() {
  return Boolean(currentReviewer && currentReviewer.can_handle !== false && currentReviewer.role !== "observer");
}

function showTab(name) {
  selectedTab = name;
  for (const tab of TABS) {
    const active = tab === name;
    $(`tab-${tab}`).classList.toggle("active", active);
    $(`tab-${tab}`).setAttribute("aria-pressed", String(active));
    $(`${tab}-panel`).hidden = !active;
  }
}

function renderAnalytics(stats, pendingList, stpAuto) {
  const allowed = canHandle();
  if ($("stp-toggle")) {
    $("stp-toggle").checked = Boolean(stpAuto);
    $("stp-toggle").disabled = !allowed;
  }
  const greenPending = (pendingList || []).filter(
    (t) => t.status === "pending" && (t.stp_tier === "STP_L1_GREEN" || t.merchant_bear_yuan === 0)
  );
  const batchBtn = $("stp-batch-btn");
  if (batchBtn) {
    batchBtn.hidden = !allowed || greenPending.length === 0;
    batchBtn.textContent = `一键转准时保池直赔（${greenPending.length} 单 · 本店¥0）`;
  }
  if (!stats) return;
  if ($("kpi-platform-saved")) $("kpi-platform-saved").textContent = `¥${Number(stats.platform_subrogation_saved_yuan || 0).toFixed(1)}`;
  if ($("kpi-merchant-cost")) $("kpi-merchant-cost").textContent = `¥${Number(stats.merchant_net_cost_yuan || 0).toFixed(1)}`;
  if ($("kpi-stp-guard")) {
    const dupSuffix = stats.duplicate_evidence_alerts ? ` · 重复图 ${stats.duplicate_evidence_alerts}` : "";
    $("kpi-stp-guard").textContent = `${stats.stp_green_eligible || 0} 单 / 拦截 ${stats.guardrail_intercepts || 0}${dupSuffix}`;
  }
  if ($("kpi-csat-chain")) {
    const csat = stats.avg_csat ? `${stats.avg_csat} ★` : "待评";
    const chain = stats.audit_chain_intact === false ? "异常" : `完好 (${stats.audit_entries || 0})`;
    $("kpi-csat-chain").textContent = `${csat} · ${chain}`;
  }
}

function ticketCard(ticket) {
  const card = el("article", `ticket ticket-${ticket.status}`);
  card.dataset.ticketId = ticket.ticket_id;
  const head = el("div", "ticket-head");
  const heading = el("strong", "", ticket.order_id);
  heading.append(el("small", "", ticket.ticket_id));
  head.append(heading, badge(ticket.status));
  const person = el("div", "review-person");
  const itemSummary = Array.isArray(ticket.items) && ticket.items.length ? ticket.items.join("、") : "标准套餐";
  person.append(
    el("span", "avatar", "U"),
    el("span", "", `顾客 ${ticket.customer_id} · 实付 ¥${ticket.amount_yuan ?? "—"}（${itemSummary}）`),
    el("time", "", clock(ticket.created_at))
  );
  const grid = el("div", "review-facts");
  const bearNote = typeof ticket.merchant_bear_yuan === "number"
    ? `¥${ticket.proposed_coupon_yuan}（本店 ¥${ticket.merchant_bear_yuan.toFixed(1)}）`
    : `¥${ticket.proposed_coupon_yuan}`;
  const rows = [
    ["预计送达", ticket.expected_at],
    ["实际送达", ticket.delivered_at],
    ["晚到时长", delayText(ticket.late_seconds)],
    ["申请补偿", bearNote],
  ];
  for (const [label, value] of rows) {
    const item = el("div", `review-fact${label === "申请补偿" ? " emphasis" : ""}`);
    item.append(el("span", "", label), el("strong", "", value));
    grid.append(item);
  }
  card.append(head, person, grid);
  const chain = fulfillmentChain(ticket);
  if (chain) card.append(chain);
  const attr = attributionBox(ticket);
  if (attr) card.append(attr);
  if (ticket.order_attachments && ticket.order_attachments.length) {
    const attBlock = attachmentList(ticket.order_attachments);
    attBlock.classList.add("review-attachments");
    card.append(attBlock);
  }
  if (ticket.information_request) {
    const request = el("div", "information-request");
    request.append(el("span", "", "补充要求"), el("p", "", ticket.information_request));
    card.append(request);
  }
  if (ticket.customer_information) {
    const information = el("div", "customer-information");
    information.append(el("span", "", "顾客补充"), el("p", "", ticket.customer_information));
    card.append(information);
  }
  return card;
}

function pendingCard(ticket) {
  const card = ticketCard(ticket);
  if (ticket.status === "needs_info") {
    const waiting = el("p", "waiting-information");
    waiting.append(icon("clock"), el("span", "", "等待顾客补充说明或图片凭证"));
    card.append(waiting, ticketHistory(ticket.ticket_id));
    return card;
  }
  if (!canHandle()) {
    const ro = el("p", "readonly-role-banner", "当前坐席为只读观察权限，不可执行审批操作。");
    card.append(ro, ticketHistory(ticket.ticket_id));
    return card;
  }
  const noteId = `review-note-${ticket.ticket_id}`;
  const label = el("label", "note-label", "处理说明");
  label.htmlFor = noteId;
  label.append(el("span", "", "拒绝或请补充时必填 · 200 字"));
  const note = el("textarea", "note");
  note.id = noteId;
  note.rows = 3;
  note.maxLength = 200;
  note.placeholder = "填写通过说明、具体驳回原因，或需要顾客补充的信息";
  note.dataset.ticket = ticket.ticket_id;
  note.value = drafts.get(ticket.ticket_id) || "";
  note.addEventListener("input", () => { drafts.set(ticket.ticket_id, note.value); note.removeAttribute("aria-invalid"); });
  const quickRow = el("div", "quick-notes");
  for (const preset of [
    "本店按时出餐，转交平台准时保池全额赔付（豁免骑手高峰扣款）。",
    "67餐厅高峰备餐致歉，同意按清分比例发放无门槛补偿券。",
    "经核实配送时段遇临时交通管制，本次暂不符合发券条件，如有疑问可转人工复核。",
    "请补充外卖送达位置照片或截图以便核验。",
  ]) {
    const chip = button(`快捷：${preset.slice(0, 10)}…`, "quick-chip", () => {
      note.value = preset;
      drafts.set(ticket.ticket_id, preset);
      note.removeAttribute("aria-invalid");
      note.focus();
    });
    quickRow.append(chip);
  }
  const actions = el("div", "actions");
  const requestInfo = button("请顾客补充", "secondary request-info-button", () => decide(ticket.ticket_id, "request_info"));
  requestInfo.dataset.action = "request-info";
  requestInfo.prepend(icon("chat"));
  const reject = button("拒绝", "danger", () => decide(ticket.ticket_id, "reject"));
  const approve = button("通过", "primary", () => decide(ticket.ticket_id, "approve"));
  approve.prepend(icon("check"));
  actions.append(requestInfo);
  if (ticket.merchant_bear_yuan === 0 || ticket.stp_tier === "STP_L1_GREEN") {
    const subrogateBtn = button("转准时保池直赔（本店¥0）", "secondary stp-direct-btn", () => {
      if (!(drafts.get(ticket.ticket_id) || "").trim()) {
        drafts.set(ticket.ticket_id, "平台准时保池 100% 直赔（本店按时出餐 ¥0 承担）");
      }
      decide(ticket.ticket_id, "approve");
    });
    actions.append(subrogateBtn);
  }
  actions.append(reject, approve);
  card.append(label, quickRow, note, actions, ticketHistory(ticket.ticket_id));
  return card;
}

function decidedCard(ticket) {
  const card = ticketCard(ticket);
  const result = el("div", "ticket-highlight");
  const text = el("div");
  const reviewerTag = ticket.reviewer_id === "STP_ENGINE" ? "准时保直通引擎自动秒批" : ticket.reviewer_id;
  text.append(
    el("h3", "", ticket.status === "approved" ? `已发放 ¥${ticket.coupon_issued_yuan} 补偿券` : "已驳回"),
    el("p", "", `${clock(ticket.decided_at)} · ${reviewerTag}`)
  );
  result.append(icon(ticket.status === "approved" ? "check" : "close"), text);
  card.append(result);
  if (ticket.review_note) {
    const note = el("div", "ticket-note");
    note.append(el("span", "", "处理说明"), el("p", "", ticket.review_note));
    card.append(note);
  }
  const rating = el("p", `review-rating${ticket.rating ? " rated" : ""}`);
  if (ticket.rating) rating.append(icon("star"), el("span", "", `顾客评价 ${ticket.rating} / 5`));
  else rating.append(el("span", "", "顾客暂未评价"));
  card.append(rating, ticketHistory(ticket.ticket_id));
  return card;
}

function openActionConfirm({ title, desc, rows, danger = false, payload, handoffId }) {
  const dlg = $("action-confirm-dialog");
  if (!dlg) return executeHandoffAction(handoffId, payload);
  $("action-confirm-title").textContent = title;
  $("action-confirm-desc").textContent = desc;
  $("action-confirm-facts").replaceChildren(...factRows(rows));
  const submitBtn = $("action-confirm-submit");
  submitBtn.className = danger ? "danger-solid" : "primary";
  pendingConfirmAction = { handoffId, payload };
  dlg.showModal();
}

function actionTimeline(item) {
  const logs = item.action_logs || [];
  if (!logs.length) return null;
  const wrap = el("div", "action-timeline");
  wrap.append(el("span", "action-timeline-title", "处理流水时间线（操作人 · 时间 · 动作 · 状态变更）"));
  const list = el("ol", "history-list");
  for (const entry of logs) {
    const row = el("li", `history-event${entry.is_internal ? " is-internal-log" : ""}`);
    const head = el("div", "history-event-head");
    const left = el("strong", "", `${entry.action_label || entry.action}`);
    if (entry.is_internal) left.append(el("span", "internal-tag", "仅内部"));
    head.append(left, el("time", "", clock(entry.at)));
    row.append(head);
    const parts = [`操作人：${entry.actor_name || entry.actor_id}`];
    if (entry.before_status || entry.after_status) {
      const b = TICKET_STATE_LABELS[entry.before_status] || entry.before_status || "—";
      const a = TICKET_STATE_LABELS[entry.after_status] || entry.after_status || "—";
      parts.push(`状态：${b} → ${a}`);
    }
    if (typeof entry.amount_yuan === "number") parts.push(`金额：¥${entry.amount_yuan}`);
    row.append(el("small", "history-meta", parts.join(" ｜ ")));
    if (entry.note) row.append(el("p", "", entry.note));
    list.append(row);
  }
  wrap.append(list);
  return wrap;
}

function handoffActionZone(item) {
  const hid = item.handoff_id;
  if (!canHandle()) {
    return el("p", "readonly-role-banner", "当前坐席为只读观察权限，不可操作处理按键（仅可查看会话与流水）。");
  }
  if (item.status === "cancelled") return null;

  const rt = item.related_ticket;
  const zone = el("section", "handoff-action-zone");
  zone.setAttribute("aria-label", "处理动作区");

  const header = el("div", "action-zone-head");
  const stLabel = rt ? (TICKET_STATE_LABELS[rt.status] || rt.status) : "暂无关联申请单";
  header.append(
    el("strong", "", "处理动作区"),
    el("span", `badge badge-${rt ? rt.status : "waiting"}`, rt ? `${rt.ticket_id} · ${stLabel}` : "订单维度处理")
  );
  zone.append(header);

  const defaultAmt = rt && rt.proposed_coupon_yuan ? rt.proposed_coupon_yuan : 10;
  const needAmount = !rt || rt.status !== "approved";
  const amountInputId = `handoff-action-amount-${hid}`;
  let amountInput = null;
  if (needAmount) {
    const amtRow = el("div", "action-amount-row");
    const amtLabel = el("label", "", "补偿金额 (¥)");
    amtLabel.htmlFor = amountInputId;
    amountInput = el("input", "action-amount-input");
    amountInput.id = amountInputId;
    amountInput.type = "number";
    amountInput.min = "1";
    amountInput.max = "500";
    amountInput.step = "1";
    amountInput.dataset.actionAmount = hid;
    amountInput.value = actionAmountDrafts.has(hid) ? actionAmountDrafts.get(hid) : String(defaultAmt);
    amountInput.addEventListener("input", () => actionAmountDrafts.set(hid, amountInput.value));
    amtRow.append(amtLabel, amountInput, el("span", "action-amount-hint", "默认 ¥10，可按实情调整（1–500）"));
    zone.append(amtRow);
  }

  const noteId = `handoff-action-note-${hid}`;
  const noteLabel = el("label", "note-label", "处理理由 / 备注说明");
  noteLabel.htmlFor = noteId;
  noteLabel.append(el("span", "", "驳回、补充材料、内部备注时必填"));
  const noteInput = el("textarea", "note action-note-input");
  noteInput.id = noteId;
  noteInput.rows = 2;
  noteInput.maxLength = 300;
  noteInput.placeholder = "填写给顾客看的驳回原因/补偿说明，或填写仅内部可见的备注…";
  noteInput.dataset.actionNote = hid;
  noteInput.value = actionNoteDrafts.get(hid) || "";
  noteInput.addEventListener("input", () => {
    actionNoteDrafts.set(hid, noteInput.value);
    noteInput.removeAttribute("aria-invalid");
  });
  zone.append(noteLabel, noteInput);

  const readNote = () => (actionNoteDrafts.get(hid) || "").trim();
  const readAmount = () => {
    const raw = actionAmountDrafts.has(hid) ? actionAmountDrafts.get(hid) : String(defaultAmt);
    const num = Number(raw);
    return Number.isFinite(num) && num >= 1 ? Math.round(num) : defaultAmt;
  };
  const requireNote = (msg) => {
    const val = readNote();
    if (!val) {
      noteInput.setAttribute("aria-invalid", "true");
      noteInput.focus();
      showStatus(msg, true);
      return null;
    }
    return val;
  };

  if (rt) {
    const tGroup = el("div", "action-group");
    tGroup.append(el("span", "action-group-label", `申请单处理（${rt.ticket_id} · ${stLabel}）`));
    const tBtns = el("div", "actions action-btn-row");
    if (rt.status === "rejected") {
      const amtBtn = button(`同意补偿（默认¥${defaultAmt}）`, "primary small", () => {
        const amt = readAmount();
        openActionConfirm({
          handoffId: hid,
          title: "确认同意补偿？",
          desc: "将把已驳回申请单改判为通过并立即发放补偿券，顾客端同步可见并追加系统消息。",
          rows: [["订单 / 申请单", `${item.order_id} · ${rt.ticket_id}`], ["状态变更", "已驳回 → 已通过"], ["发放金额", `¥${amt}`], ["说明", readNote() || `人工客服核实通过，发放 ¥${amt} 无门槛补偿券。`]],
          payload: { action: "approve_compensation", amount_yuan: amt, note: readNote() },
        });
      });
      amtBtn.dataset.handoffAction = "approve_compensation";

      const upholdBtn = button("维持驳回", "danger small", () => {
        const reason = requireNote("维持驳回必须填写具体理由（顾客可见）。");
        if (!reason) return;
        openActionConfirm({
          handoffId: hid, danger: true,
          title: "确认维持驳回？",
          desc: "申请单将维持「已驳回」状态，填写的驳回理由将同步展示给顾客。",
          rows: [["订单 / 申请单", `${item.order_id} · ${rt.ticket_id}`], ["状态变更", "已驳回 → 已驳回（更新理由）"], ["驳回理由（顾客可见）", reason]],
          payload: { action: "uphold_reject", note: reason },
        });
      });
      upholdBtn.dataset.handoffAction = "uphold_reject";

      const reqBtn = button("要求补充材料", "secondary small", () => {
        const reason = requireNote("请填写需要顾客补充的材料说明。");
        if (!reason) return;
        openActionConfirm({
          handoffId: hid,
          title: "确认要求补充材料？",
          desc: "申请单将流转为「待补充」，顾客端将出现材料提交表单。",
          rows: [["订单 / 申请单", `${item.order_id} · ${rt.ticket_id}`], ["状态变更", "已驳回 → 待补充"], ["补充要求", reason]],
          payload: { action: "request_info", note: reason },
        });
      });
      reqBtn.dataset.handoffAction = "request_info";

      const escBtn = button("升级主管", "secondary small", () => {
        openActionConfirm({
          handoffId: hid,
          title: "确认升级主管处理？",
          desc: "将标记为升级主管专席并写入处理流水与系统提示。",
          rows: [["订单 / 申请单", `${item.order_id} · ${rt.ticket_id}`], ["动作", "升级主管"], ["说明", readNote() || "已升级主管专席复核处理"]],
          payload: { action: "escalate", note: readNote() },
        });
      });
      escBtn.dataset.handoffAction = "escalate";
      tBtns.append(amtBtn, upholdBtn, reqBtn, escBtn);
    } else if (rt.status === "pending") {
      const passBtn = button("通过", "primary small", () => {
        const amt = readAmount();
        openActionConfirm({
          handoffId: hid,
          title: "确认通过申请？",
          desc: "将审核通过该申请单并发放对应补偿券，顾客端同步可见。",
          rows: [["订单 / 申请单", `${item.order_id} · ${rt.ticket_id}`], ["状态变更", "待审核 → 已通过"], ["发放金额", `¥${amt}`], ["说明", readNote() || `人工客服核实通过，发放 ¥${amt} 无门槛补偿券。`]],
          payload: { action: "approve", amount_yuan: amt, note: readNote() },
        });
      });
      passBtn.dataset.handoffAction = "approve";

      const rejBtn = button("驳回", "danger small", () => {
        const reason = requireNote("驳回申请必须填写具体理由（顾客可见）。");
        if (!reason) return;
        openActionConfirm({
          handoffId: hid, danger: true,
          title: "确认驳回申请？",
          desc: "申请单将变为「已驳回」，填写的驳回理由将同步展示给顾客。",
          rows: [["订单 / 申请单", `${item.order_id} · ${rt.ticket_id}`], ["状态变更", "待审核 → 已驳回"], ["驳回理由（顾客可见）", reason]],
          payload: { action: "reject", note: reason },
        });
      });
      rejBtn.dataset.handoffAction = "reject";

      const expBtn = button("加急", "secondary small", () => executeHandoffAction(hid, { action: "expedite", note: readNote() }));
      expBtn.dataset.handoffAction = "expedite";

      const targetSelect = el("select", "transfer-select");
      targetSelect.setAttribute("aria-label", "转交目标坐席");
      const targets = allReviewers.filter((r) => r.can_handle !== false && r.reviewer_id !== (currentReviewer && currentReviewer.reviewer_id));
      for (const t of (targets.length ? targets : allReviewers.filter((r) => r.can_handle !== false))) {
        const opt = document.createElement("option");
        opt.value = t.reviewer_id;
        opt.textContent = t.display_name;
        targetSelect.append(opt);
      }
      const transBtn = button("转交", "secondary small", () => executeHandoffAction(hid, {
        action: "transfer",
        target_reviewer_id: targetSelect.value || undefined,
        note: readNote(),
      }));
      transBtn.dataset.handoffAction = "transfer";
      tBtns.append(passBtn, rejBtn, expBtn, targetSelect, transBtn);
    } else if (rt.status === "needs_info") {
      const passBtn = button("直接同意补偿", "primary small", () => {
        const amt = readAmount();
        openActionConfirm({
          handoffId: hid,
          title: "确认直接通过补偿？",
          desc: "将跳过等待补充材料并直接通过发放补偿券。",
          rows: [["订单 / 申请单", `${item.order_id} · ${rt.ticket_id}`], ["状态变更", "待补充 → 已通过"], ["发放金额", `¥${amt}`]],
          payload: { action: "approve_compensation", amount_yuan: amt, note: readNote() },
        });
      });
      const expBtn = button("加急", "secondary small", () => executeHandoffAction(hid, { action: "expedite", note: readNote() }));
      const transBtn = button("转交", "secondary small", () => executeHandoffAction(hid, { action: "transfer", note: readNote() }));
      tBtns.append(passBtn, expBtn, transBtn);
    } else if (rt.status === "approved") {
      const reopenBtn = button("重新开启", "secondary small", () => {
        openActionConfirm({
          handoffId: hid,
          title: "确认重新开启申请单？",
          desc: "将把已通过的申请单重新恢复为「待审核」状态以便复核。",
          rows: [["订单 / 申请单", `${item.order_id} · ${rt.ticket_id}`], ["状态变更", "已通过 → 待审核"], ["说明", readNote() || "坐席重新开启申请单进入待审核"]],
          payload: { action: "reopen", note: readNote() },
        });
      });
      reopenBtn.dataset.handoffAction = "reopen";
      tBtns.append(reopenBtn, el("span", "action-readonly-hint", `已发券 ¥${rt.coupon_issued_yuan ?? rt.proposed_coupon_yuan}（下方可查完整处理流水）`));
    }
    tGroup.append(tBtns);
    zone.append(tGroup);
  }

  const oGroup = el("div", "action-group");
  oGroup.append(el("span", "action-group-label", "订单维度动作（始终可用）"));
  const oBtns = el("div", "actions action-btn-row");
  if (item.order_id) {
    const urgeBtn = button("催单提醒", "secondary small", () => executeHandoffAction(hid, { action: "urge_or_reassign", mode: "urge", note: readNote() }));
    urgeBtn.dataset.handoffAction = "urge";
    const reassignBtn = button("改派运力", "secondary small", () => executeHandoffAction(hid, { action: "urge_or_reassign", mode: "reassign", note: readNote() }));
    reassignBtn.dataset.handoffAction = "reassign";
    oBtns.append(urgeBtn, reassignBtn);
  }
  const internalBtn = button("添加内部备注", "secondary small", () => {
    const text = requireNote("请先填写内部备注内容（仅坐席内部可见）。");
    if (!text) return;
    executeHandoffAction(hid, { action: "internal_note", note: text });
  });
  internalBtn.dataset.handoffAction = "internal_note";
  oBtns.append(internalBtn);

  if (item.order_id && !rt) {
    const createBtn = button("创建工单", "primary small", () => {
      const amt = readAmount();
      openActionConfirm({
        handoffId: hid,
        title: "确认创建售后工单？",
        desc: "将为当前订单创建「待审核」申请单，创建后可立即在动作区审批通过或驳回。",
        rows: [["关联订单", item.order_id], ["状态变更", "无工单 → 待审核"], ["建议金额", `¥${amt}`], ["说明", readNote() || "人工客服在会话内为顾客创建售后申请单"]],
        payload: { action: "create_ticket", amount_yuan: amt, note: readNote() },
      });
    });
    createBtn.dataset.handoffAction = "create_ticket";
    oBtns.append(createBtn);
  }

  if (!item.ended_at) {
    const closeBtn = button("结束会话", "danger small", () => {
      openActionConfirm({
        handoffId: hid, danger: true,
        title: "确认结束本次人工会话？",
        desc: "会话状态将流转为「已结束」，不再停留于待回复，并向顾客发送结束提示。",
        rows: [["会话单号", hid], ["状态变更", `${HANDOFF_STATUS[item.status] || item.status} → 已结束`], ["结案说明", readNote() || "问题已核实处理完毕，本次人工服务结束"]],
        payload: { action: "close_session", note: readNote() },
      });
    });
    closeBtn.dataset.handoffAction = "close_session";
    oBtns.append(closeBtn);
  }
  oGroup.append(oBtns);
  zone.append(oGroup);
  return zone;
}

function handoffCard(item) {
  const isP0 = item.priority === "P0_FOOD_SAFETY";
  const needsReply = Boolean(item.needs_specialist_reply);
  const isEnded = Boolean(item.ended_at);
  const card = el("article", `ticket handoff handoff-${item.status}${isEnded ? " is-ended" : ""}${isP0 ? " is-p0-handoff" : ""}${needsReply ? " is-needs-reply" : ""}`);
  card.dataset.handoffId = item.handoff_id;
  const head = el("div", "ticket-head");
  const heading = el("strong", "", item.order_id || "未指明订单");
  heading.append(el("small", "", item.handoff_id));
  const badgeWrap = el("div", "handoff-badges");
  if (isP0) badgeWrap.append(el("span", "p0-badge", "P0 食安紧急专案"));
  if (item.is_expedited) badgeWrap.append(el("span", "badge badge-expedited", "加急"));
  if (item.escalated_to) badgeWrap.append(el("span", "badge badge-escalated", `已升级：${item.escalated_to}`));
  if (item.assigned_reviewer_id) badgeWrap.append(el("span", "badge badge-assigned", `指派：${item.assigned_reviewer_id}`));
  if (needsReply) badgeWrap.append(el("span", "badge badge-pending", "顾客新消息待回"));
  const badgeKey = isEnded ? "ended" : item.status;
  badgeWrap.append(el("span", `badge badge-${badgeKey}`, HANDOFF_STATUS[badgeKey] || item.status));
  head.append(heading, badgeWrap);
  const person = el("div", "review-person");
  const summary = item.order_summary;
  const orderBrief = summary
    ? ` · ${summary.merchant || "67餐厅"} · 实付 ¥${summary.amount_yuan}（${(summary.items || []).join("、")}）`
    : "";
  person.append(el("span", "avatar", "U"), el("span", "", `顾客 ${item.customer_id}${orderBrief}`), el("time", "", clock(item.created_at)));
  card.append(head, person);
  if (summary) {
    const orderRows = [
      ["关联订单", `${item.order_id} · ${summary.status === "delivered" ? "已送达" : "配送中"}`],
      ["预计 / 实际送达", `${summary.expected_at || "—"} → ${summary.delivered_at || "配送中"}`],
    ];
    if (item.related_ticket) {
      const rt = item.related_ticket;
      const rtNote = rt.review_note ? `（说明：${rt.review_note}）` : "";
      orderRows.push(["关联申请单", `${rt.ticket_id} · ${STATUS_TEXT[rt.status] || rt.status}${rtNote}`]);
    }
    card.append(facts(orderRows));
    const attr = attributionBox(summary);
    if (attr) card.append(attr);
  }
  if (item.initial_appeal) {
    const appealBox = el("div", "information-request initial-appeal-box");
    appealBox.append(el("span", "", "最初诉求"), el("p", "", item.initial_appeal));
    card.append(appealBox);
  }
  if (item.request_text && item.request_text !== item.initial_appeal) {
    const request = el("div", "information-request");
    request.append(el("span", "", "转人工留言"), el("p", "", item.request_text));
    card.append(request);
  }
  if (item.attachments && item.attachments.length) {
    const attachments = attachmentList(item.attachments);
    attachments.classList.add("review-attachments");
    card.append(attachments);
  }
  const transcript = el("ol", "handoff-transcript");
  for (const line of item.excerpt) {
    const row = el("li", `line-${line.role}`);
    row.append(el("span", "line-role", LINE_ROLE[line.role] || line.role), el("p", "", line.text));
    transcript.append(row);
  }
  if (!item.excerpt.length) transcript.append(el("li", "line-empty", "顾客直接转人工，暂无对话"));
  card.append(el("span", "transcript-label", "转人工前的对话"), transcript);
  if (item.status === "waiting") {
    const actionZone = handoffActionZone(item);
    if (actionZone) card.append(actionZone);
    if (canHandle()) {
      const replyId = `handoff-reply-${item.handoff_id}`;
      const label = el("label", "note-label", "回复顾客");
      label.htmlFor = replyId;
      label.append(el("span", "", "顾客在对话里看到 · 500 字"));
      const note = el("textarea", "note");
      note.id = replyId;
      note.rows = 3;
      note.maxLength = 500;
      note.placeholder = "例如：已看到你的情况，正在为你核实跟进";
      note.dataset.handoff = item.handoff_id;
      note.value = replyDrafts.get(item.handoff_id) || "";
      note.addEventListener("input", () => { replyDrafts.set(item.handoff_id, note.value); note.removeAttribute("aria-invalid"); });
      const quickReplies = el("div", "quick-notes");
      const presets = isP0
        ? [
            "非常抱歉让您遇到餐品问题！我是67餐厅食安主管，已收到您的照片凭证并为您优先登记全额售后处理。",
            "您好，我们已封存同批次后厨留样核查，稍后继续在此向您同步处理结果。",
          ]
        : [
            "你好，我是67餐厅专席客服，已看到你的订单情况，正在为你核对备餐与配送记录。",
            "非常抱歉让你久等了，已为你优先登记准时保关怀跟进。",
          ];
      for (const preset of presets) {
        const chip = button(`快捷：${preset.slice(0, 10)}…`, "quick-chip", () => {
          note.value = preset;
          replyDrafts.set(item.handoff_id, preset);
          note.removeAttribute("aria-invalid");
          note.focus();
        });
        quickReplies.append(chip);
      }
      const actions = el("div", "actions");
      const send = button("发送回复", "primary", () => reply(item.handoff_id));
      send.dataset.action = "handoff-reply";
      send.prepend(icon("arrow-up"));
      actions.append(send);
      card.append(label, quickReplies, note, actions);
    }
  } else if (item.status === "replied") {
    if (item.reply_text) {
      const note = el("div", "ticket-note");
      note.append(el("span", "", `首次回复 · ${clock(item.closed_at)} · ${item.reviewer_id}`), el("p", "", item.reply_text));
      card.append(note);
    }
    for (const f of item.followups || []) {
      const fNode = el("div", `ticket-note followup-note${f.sender_role === "system" ? " is-system-followup" : ""}`);
      const roleLabel = f.sender_role === "customer"
        ? "顾客追加留言"
        : (f.sender_role === "system" ? "系统通知（顾客可见）" : `专员追加跟进 · ${f.sender_id || "坐席"}`);
      fNode.append(el("span", "", `${roleLabel} · ${clock(f.created_at)}`), el("p", "", f.text));
      card.append(fNode);
    }
    const actionZone = handoffActionZone(item);
    if (actionZone) card.append(actionZone);
    if (canHandle()) {
      const isExpanded = expandedFollowups.has(item.handoff_id) || needsReply;
      if (!isExpanded) {
        const toggleRow = el("div", "actions followup-toggle-row");
        const openBtn = button("追加跟进回复", "secondary small", () => {
          expandedFollowups.add(item.handoff_id);
          lastTickets = "";
          refresh();
        });
        openBtn.prepend(icon("chat"));
        toggleRow.append(openBtn);
        card.append(toggleRow);
      } else {
        const wrap = el("div", "handoff-followup-box");
        const fInput = el("textarea", "note");
        fInput.id = `handoff-followup-${item.handoff_id}`;
        fInput.rows = 2;
        fInput.maxLength = 500;
        fInput.placeholder = "输入后续核查进展，顾客端将实时收到追加气泡…";
        fInput.dataset.followup = item.handoff_id;
        fInput.value = followupDrafts.get(item.handoff_id) || "";
        fInput.addEventListener("input", () => followupDrafts.set(item.handoff_id, fInput.value));
        const fActions = el("div", "actions");
        const cancelBtn = button("收起", "secondary small", () => {
          expandedFollowups.delete(item.handoff_id);
          lastTickets = "";
          refresh();
        });
        const sendFollowup = button("发送追加回复", "primary small", () => sendHandoffFollowup(item.handoff_id));
        fActions.append(cancelBtn, sendFollowup);
        wrap.append(fInput, fActions);
        card.append(wrap);
      }
    }
  } else {
    const waiting = el("p", "waiting-information");
    waiting.append(icon("close"), el("span", "", `顾客已于 ${clock(item.closed_at)} 取消`));
    card.append(waiting);
  }
  const timeline = actionTimeline(item);
  if (timeline) card.append(timeline);
  return card;
}

function renderList(id, tickets, makeCard) {
  if (tickets.length) { $(id).replaceChildren(...tickets.map(makeCard)); return; }
  $(id).replaceChildren(emptyState(id === "pending" ? "inbox" : "file-check", id === "pending" ? "暂无待处理申请" : "暂无处理记录", "", true));
}

function renderHandoffs(data) {
  const waitingIds = new Set(data.waiting.map((item) => item.handoff_id));
  for (const id of replyDrafts.keys()) if (!waitingIds.has(id)) replyDrafts.delete(id);
  const activeFollowups = data.closed.filter((item) => item.needs_specialist_reply);
  const restClosed = data.closed.filter((item) => !item.needs_specialist_reply);
  const actionableCount = data.waiting.length + activeFollowups.length;
  $("handoffs-count").textContent = actionableCount;
  $("tab-handoffs").classList.toggle("has-waiting", actionableCount > 0);
  const items = [...data.waiting, ...activeFollowups.slice().reverse(), ...restClosed.slice().reverse()];
  if (items.length) $("handoffs").replaceChildren(...items.map(handoffCard));
  else $("handoffs").replaceChildren(emptyState("chat", "暂无人工咨询", "", true));
}

function signOut() {
  signedIn = false;
  currentReviewer = null;
  lastTickets = "";
  drafts.clear();
  replyDrafts.clear();
  followupDrafts.clear();
  actionNoteDrafts.clear();
  actionAmountDrafts.clear();
  expandedFollowups.clear();
  document.title = BASE_TITLE;
  setSignedIn(null);
}

async function refresh() {
  let data, handoffs, stats = null;
  try {
    [data, handoffs, stats] = await Promise.all([
      api("/api/review/tickets"),
      api("/api/review/handoffs"),
      api("/api/review/analytics").catch(() => null),
    ]);
  } catch (error) {
    if (error.status === 401) return signOut();
    throw error;
  }
  const key = JSON.stringify([data, handoffs, stats, [...expandedFollowups], currentReviewer && currentReviewer.reviewer_id]);
  if (key === lastTickets) return;
  lastTickets = key;
  const active = document.activeElement;
  const field = active && (active.dataset.ticket || active.dataset.handoff || active.dataset.followup || active.dataset.actionNote || active.dataset.actionAmount) ? active : null;
  const selector = field
    ? (field.dataset.ticket
      ? `textarea[data-ticket="${CSS.escape(field.dataset.ticket)}"]`
      : field.dataset.handoff
      ? `textarea[data-handoff="${CSS.escape(field.dataset.handoff)}"]`
      : field.dataset.followup
      ? `textarea[data-followup="${CSS.escape(field.dataset.followup)}"]`
      : field.dataset.actionNote
      ? `textarea[data-action-note="${CSS.escape(field.dataset.actionNote)}"]`
      : `input[data-action-amount="${CSS.escape(field.dataset.actionAmount)}"]`)
    : null;
  const start = field ? field.selectionStart : 0;
  const end = field ? field.selectionEnd : 0;

  pendingCountSnapshot = data.pending.filter((t) => t.status === "pending").length;
  const urgentTotal = pendingCountSnapshot + handoffs.waiting.length;
  document.title = urgentTotal > 0 ? `(待办 ${urgentTotal}) ${BASE_TITLE}` : BASE_TITLE;

  $("pending-count").textContent = data.pending.length;
  $("decided-count").textContent = data.decided.length;
  renderAnalytics(stats, data.pending, data.stp_auto_approve);
  renderList("pending", data.pending, pendingCard);
  renderList("decided", data.decided.slice().reverse(), decidedCard);
  renderHandoffs(handoffs);
  if (selector) {
    const note = document.querySelector(selector);
    if (note) { note.focus({ preventScroll: true }); if (typeof note.setSelectionRange === "function" && start !== null) note.setSelectionRange(start, end); }
  }
}

async function executeHandoffAction(handoffId, payload) {
  if (busy) return;
  busy = true;
  for (const node of document.querySelectorAll("#handoffs button, #handoffs textarea, #handoffs input")) node.disabled = true;
  showStatus("正在执行业务处理动作…");
  try {
    const res = await api(`/api/review/handoffs/${encodeURIComponent(handoffId)}/action`, payload);
    if (payload.action !== "internal_note") actionNoteDrafts.delete(handoffId);
    else actionNoteDrafts.delete(handoffId);
    if (res.action_log) {
      showStatus(`${handoffId} · 已完成「${res.action_log.action_label}」`);
    } else {
      showStatus(`${handoffId} · 处理完成`);
    }
  } catch (error) { showStatus(error.message, true); }
  finally {
    busy = false;
    lastTickets = "";
    await refresh().catch((error) => showStatus(error.message, true));
  }
}

async function decide(ticketId, decision) {
  if (busy) return;
  if ((decision === "request_info" || decision === "reject") && !(drafts.get(ticketId) || "").trim()) {
    const note = document.getElementById(`review-note-${ticketId}`);
    note.setAttribute("aria-invalid", "true");
    note.focus();
    showStatus(decision === "reject" ? "请填写具体驳回原因，方便顾客查看说明" : "请填写需要顾客补充的信息", true);
    return;
  }
  const otherPendingRemain = pendingCountSnapshot > 1;
  busy = true;
  for (const node of document.querySelectorAll("#pending button, #pending textarea")) node.disabled = true;
  showStatus("处理中…");
  try {
    const path = `/api/review/tickets/${encodeURIComponent(ticketId)}/decision`;
    const result = await api(path, { decision, note: drafts.get(ticketId) || "" });
    drafts.delete(ticketId);
    showStatus(`${ticketId} · ${STATUS_TEXT[result.ticket.status]}`);
    // Stay on "pending" during multi-ticket peak batches; switch to "decided" once the queue is cleared!
    if (decision === "request_info" || otherPendingRemain) {
      showTab("pending");
    } else {
      showTab("decided");
    }
  } catch (error) { showStatus(error.message, true); }
  finally {
    busy = false;
    lastTickets = "";
    await refresh().catch((error) => showStatus(error.message, true));
  }
}

async function reply(handoffId) {
  if (busy) return;
  const text = (replyDrafts.get(handoffId) || "").trim();
  if (!text) {
    const note = document.getElementById(`handoff-reply-${handoffId}`);
    note.setAttribute("aria-invalid", "true");
    note.focus();
    showStatus("请填写回复内容", true);
    return;
  }
  busy = true;
  for (const node of document.querySelectorAll("#handoffs button, #handoffs textarea")) node.disabled = true;
  showStatus("处理中…");
  try {
    await api(`/api/review/handoffs/${encodeURIComponent(handoffId)}/reply`, { text });
    replyDrafts.delete(handoffId);
    showStatus(`${handoffId} · 已回复顾客`);
  } catch (error) { showStatus(error.message, true); }
  finally {
    busy = false;
    lastTickets = "";
    await refresh().catch((error) => showStatus(error.message, true));
  }
}

async function sendHandoffFollowup(handoffId) {
  if (busy) return;
  const text = (followupDrafts.get(handoffId) || "").trim();
  if (!text) {
    const fInput = document.getElementById(`handoff-followup-${handoffId}`);
    if (fInput) { fInput.setAttribute("aria-invalid", "true"); fInput.focus(); }
    showStatus("请填写追加跟进内容", true);
    return;
  }
  busy = true;
  showStatus("正在发送追加跟进…");
  try {
    await api(`/api/review/handoffs/${encodeURIComponent(handoffId)}/followup`, { text });
    followupDrafts.delete(handoffId);
    expandedFollowups.delete(handoffId);
    showStatus(`${handoffId} · 已发送追加回复`);
  } catch (error) { showStatus(error.message, true); }
  finally {
    busy = false;
    lastTickets = "";
    await refresh().catch((error) => showStatus(error.message, true));
  }
}

async function toggleStpMode(enabled) {
  try {
    await api("/api/review/stp-mode", { enabled });
    showStatus(enabled ? "已开启绿灯准时保 0 人工直通秒赔模式" : "已切换为人工复核模式");
    lastTickets = "";
    await refresh();
  } catch (error) {
    showStatus(error.message, true);
  }
}

async function runStpBatch() {
  if (busy) return;
  busy = true;
  showStatus("正在批量转交平台准时保池直赔…");
  try {
    const res = await api("/api/review/stp-batch", {});
    showStatus(`已一键直赔 ${res.count} 张绿灯运力延误单（本店 ¥0 承担）`);
    if (pendingCountSnapshot <= res.count) showTab("decided");
  } catch (error) { showStatus(error.message, true); }
  finally {
    busy = false;
    lastTickets = "";
    await refresh().catch((error) => showStatus(error.message, true));
  }
}

async function resetDemo() {
  if (busy) return;
  busy = true;
  $("reset-dialog").close();
  try {
    await api("/api/review/reset", {});
    drafts.clear();
    replyDrafts.clear();
    followupDrafts.clear();
    expandedFollowups.clear();
    showTab("pending");
    showStatus("已清空当前演示工单（底层 SHA-256 审计哈希链完好保留）");
  } catch (error) { showStatus(error.message, true); }
  finally {
    busy = false;
    lastTickets = "";
    await refresh().catch((error) => showStatus(error.message, true));
  }
}

async function enter(reviewer) {
  currentReviewer = reviewer;
  lastTickets = "";
  await refresh();
  signedIn = true;
  setSignedIn(reviewer.display_name);
}

async function boot() {
  const info = await api("/api/health");
  allReviewers = info.reviewers || [];
  renderMeta(info);
  renderLogin(info.reviewers, "reviewer_id", async (reviewerId) => {
    try { await enter((await api("/api/review/login", { reviewer_id: reviewerId })).reviewer); }
    catch (error) { showStatus(error.message, true); }
  });
  if ($("action-confirm-submit")) {
    $("action-confirm-submit").addEventListener("click", async () => {
      const pending = pendingConfirmAction;
      pendingConfirmAction = null;
      $("action-confirm-dialog").close();
      if (pending) await executeHandoffAction(pending.handoffId, pending.payload);
    });
  }
  const closeConfirm = () => {
    pendingConfirmAction = null;
    if ($("action-confirm-dialog")) $("action-confirm-dialog").close();
  };
  if ($("action-confirm-cancel")) $("action-confirm-cancel").addEventListener("click", closeConfirm);
  if ($("action-confirm-close")) $("action-confirm-close").addEventListener("click", closeConfirm);
  for (const tab of TABS) $(`tab-${tab}`).addEventListener("click", () => showTab(tab));
  if ($("stp-toggle")) {
    $("stp-toggle").addEventListener("change", (event) => toggleStpMode(event.target.checked));
  }
  if ($("stp-batch-btn")) {
    $("stp-batch-btn").addEventListener("click", runStpBatch);
  }
  $("reset").addEventListener("click", () => {
    if (busy) return;
    $("demo-dialog").close();
    $("reset-dialog").showModal();
  });
  $("reset-confirm").addEventListener("click", resetDemo);
  $("logout").addEventListener("click", async () => {
    if (busy) return;
    try { await api("/api/review/logout", {}); signOut(); }
    catch (error) { showStatus(error.message, true); }
  });
  try { await enter((await api("/api/review/me")).reviewer); }
  catch (error) { if (error.status !== 401) throw error; signOut(); }
  startPolling(() => (signedIn && !busy ? refresh() : null), 3000, { allowHidden: true });
}

boot().catch((error) => {
  showStatus(error.message, true);
  $("login").hidden = false;
  $("login-choices").replaceChildren(el("p", "status error", error.message));
});
