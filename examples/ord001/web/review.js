"use strict";

const TABS = ["pending", "decided", "handoffs"];
const HANDOFF_STATUS = { waiting: "待回复", replied: "已回复", cancelled: "顾客已取消" };
const LINE_ROLE = { customer: "顾客", assistant: "AI", tool: "查询" };
const BASE_TITLE = "配送关怀 · 67餐厅核损工作台";
const drafts = new Map();
const replyDrafts = new Map();
const followupDrafts = new Map();
const expandedFollowups = new Set();
let signedIn = false;
let busy = false;
let lastTickets = "";
let selectedTab = "pending";
let pendingCountSnapshot = 0;

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
  if ($("stp-toggle")) $("stp-toggle").checked = Boolean(stpAuto);
  const greenPending = (pendingList || []).filter(
    (t) => t.status === "pending" && (t.stp_tier === "STP_L1_GREEN" || t.merchant_bear_yuan === 0)
  );
  const batchBtn = $("stp-batch-btn");
  if (batchBtn) {
    batchBtn.hidden = greenPending.length === 0;
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
  const noteId = `review-note-${ticket.ticket_id}`;
  const label = el("label", "note-label", "处理说明");
  label.htmlFor = noteId;
  label.append(el("span", "", "选填 · 200 字"));
  const note = el("textarea", "note");
  note.id = noteId;
  note.rows = 3;
  note.maxLength = 200;
  note.placeholder = "处理原因，或需要顾客补充的信息";
  note.dataset.ticket = ticket.ticket_id;
  note.value = drafts.get(ticket.ticket_id) || "";
  note.addEventListener("input", () => { drafts.set(ticket.ticket_id, note.value); note.removeAttribute("aria-invalid"); });
  const quickRow = el("div", "quick-notes");
  for (const preset of [
    "本店按时出餐，转交平台准时保池全额赔付（豁免骑手高峰扣款）。",
    "67餐厅高峰备餐致歉，同意按清分比例发放无门槛补偿券。",
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
    el("h3", "", ticket.status === "approved" ? `已发放 ¥${ticket.coupon_issued_yuan} 补偿券` : "未通过"),
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

function handoffCard(item) {
  const isP0 = item.priority === "P0_FOOD_SAFETY";
  const card = el("article", `ticket handoff handoff-${item.status}${isP0 ? " is-p0-handoff" : ""}`);
  card.dataset.handoffId = item.handoff_id;
  const head = el("div", "ticket-head");
  const heading = el("strong", "", item.order_id || "未指明订单");
  heading.append(el("small", "", item.handoff_id));
  const badgeWrap = el("div", "handoff-badges");
  if (isP0) badgeWrap.append(el("span", "p0-badge", "P0 食安紧急专案"));
  badgeWrap.append(el("span", `badge badge-${item.status}`, HANDOFF_STATUS[item.status] || item.status));
  head.append(heading, badgeWrap);
  const person = el("div", "review-person");
  const summary = item.order_summary;
  const orderBrief = summary
    ? ` · 实付 ¥${summary.amount_yuan}（${(summary.items || []).join("、")}）`
    : "";
  person.append(el("span", "avatar", "U"), el("span", "", `顾客 ${item.customer_id}${orderBrief}`), el("time", "", clock(item.created_at)));
  card.append(head, person);
  if (summary) {
    const attr = attributionBox(summary);
    if (attr) card.append(attr);
  }
  if (item.request_text) {
    const request = el("div", "information-request");
    request.append(el("span", "", "顾客留言"), el("p", "", item.request_text));
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
  } else if (item.status === "replied") {
    const note = el("div", "ticket-note");
    note.append(el("span", "", `首次回复 · ${clock(item.closed_at)} · ${item.reviewer_id}`), el("p", "", item.reply_text));
    card.append(note);
    for (const f of item.followups || []) {
      const fNode = el("div", "ticket-note followup-note");
      const roleLabel = f.sender_role === "customer" ? "顾客追加留言" : `专员追加跟进 · ${f.sender_id || "坐席"}`;
      fNode.append(el("span", "", `${roleLabel} · ${clock(f.created_at)}`), el("p", "", f.text));
      card.append(fNode);
    }
    const isExpanded = expandedFollowups.has(item.handoff_id);
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
  } else {
    const waiting = el("p", "waiting-information");
    waiting.append(icon("close"), el("span", "", `顾客已于 ${clock(item.closed_at)} 取消`));
    card.append(waiting);
  }
  return card;
}

function renderList(id, tickets, makeCard) {
  if (tickets.length) { $(id).replaceChildren(...tickets.map(makeCard)); return; }
  $(id).replaceChildren(emptyState(id === "pending" ? "inbox" : "file-check", id === "pending" ? "暂无待处理申请" : "暂无处理记录", "", true));
}

function renderHandoffs(data) {
  const waitingIds = new Set(data.waiting.map((item) => item.handoff_id));
  for (const id of replyDrafts.keys()) if (!waitingIds.has(id)) replyDrafts.delete(id);
  $("handoffs-count").textContent = data.waiting.length;
  $("tab-handoffs").classList.toggle("has-waiting", data.waiting.length > 0);
  const items = [...data.waiting, ...data.closed.slice().reverse()];
  if (items.length) $("handoffs").replaceChildren(...items.map(handoffCard));
  else $("handoffs").replaceChildren(emptyState("chat", "暂无人工咨询", "", true));
}

function signOut() {
  signedIn = false;
  lastTickets = "";
  drafts.clear();
  replyDrafts.clear();
  followupDrafts.clear();
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
  const key = JSON.stringify([data, handoffs, stats, [...expandedFollowups]]);
  if (key === lastTickets) return;
  lastTickets = key;
  const active = document.activeElement;
  const field = active && (active.dataset.ticket || active.dataset.handoff || active.dataset.followup) ? active : null;
  const selector = field
    ? (field.dataset.ticket
      ? `textarea[data-ticket="${CSS.escape(field.dataset.ticket)}"]`
      : field.dataset.handoff
      ? `textarea[data-handoff="${CSS.escape(field.dataset.handoff)}"]`
      : `textarea[data-followup="${CSS.escape(field.dataset.followup)}"]`)
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
    if (note) { note.focus({ preventScroll: true }); note.setSelectionRange(start, end); }
  }
}

async function decide(ticketId, decision) {
  if (busy) return;
  if (decision === "request_info" && !(drafts.get(ticketId) || "").trim()) {
    const note = document.getElementById(`review-note-${ticketId}`);
    note.setAttribute("aria-invalid", "true");
    note.focus();
    showStatus("请填写需要顾客补充的信息", true);
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
  lastTickets = "";
  await refresh();
  signedIn = true;
  setSignedIn(reviewer.display_name);
}

async function boot() {
  const info = await api("/api/health");
  renderMeta(info);
  renderLogin(info.reviewers, "reviewer_id", async (reviewerId) => {
    try { await enter((await api("/api/review/login", { reviewer_id: reviewerId })).reviewer); }
    catch (error) { showStatus(error.message, true); }
  });
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
