"use strict";

const drafts = new Map();
let signedIn = false;
let busy = false;
let lastTickets = "";
let selectedTab = "pending";

function showTab(name) {
  selectedTab = name;
  for (const tab of ["pending", "decided"]) {
    const active = tab === name;
    $(`tab-${tab}`).classList.toggle("active", active);
    $(`tab-${tab}`).setAttribute("aria-pressed", String(active));
    $(`${tab}-panel`).hidden = !active;
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
  person.append(el("span", "avatar", "U"), el("span", "", `顾客 ${ticket.customer_id}`), el("time", "", clock(ticket.created_at)));
  const grid = el("div", "review-facts");
  const rows = [
    ["预计送达", ticket.expected_at], ["实际送达", ticket.delivered_at],
    ["晚到", delayText(ticket.late_seconds)], ["申请补偿", `¥${ticket.proposed_coupon_yuan}`],
  ];
  for (const [label, value] of rows) {
    const item = el("div", `review-fact${label === "申请补偿" ? " emphasis" : ""}`);
    item.append(el("span", "", label), el("strong", "", value));
    grid.append(item);
  }
  card.append(head, person, grid);
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
    waiting.append(icon("clock"), el("span", "", "等待顾客补充"));
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
  note.placeholder = "处理原因，或需要补充的信息";
  note.dataset.ticket = ticket.ticket_id;
  note.value = drafts.get(ticket.ticket_id) || "";
  note.addEventListener("input", () => { drafts.set(ticket.ticket_id, note.value); note.removeAttribute("aria-invalid"); });
  const actions = el("div", "actions");
  const approve = button("通过", "primary", () => decide(ticket.ticket_id, "approve"));
  const reject = button("拒绝", "danger", () => decide(ticket.ticket_id, "reject"));
  const requestInfo = button("请顾客补充", "secondary request-info-button", () => decide(ticket.ticket_id, "request_info"));
  requestInfo.dataset.action = "request-info";
  requestInfo.prepend(icon("chat"));
  approve.prepend(icon("check"));
  actions.append(requestInfo, reject, approve);
  card.append(label, note, actions, ticketHistory(ticket.ticket_id));
  return card;
}

function decidedCard(ticket) {
  const card = ticketCard(ticket);
  const result = el("div", "ticket-highlight");
  const text = el("div");
  text.append(el("h3", "", ticket.status === "approved" ? `已发放 ¥${ticket.coupon_issued_yuan} 补偿券` : "未通过"),
    el("p", "", `${clock(ticket.decided_at)} · ${ticket.reviewer_id}`));
  result.append(icon(ticket.status === "approved" ? "check" : "close"), text);
  card.append(result);
  if (ticket.review_note) {
    const note = el("div", "ticket-note");
    note.append(el("span", "", "处理说明"), el("p", "", ticket.review_note));
    card.append(note);
  }
  card.append(ticketHistory(ticket.ticket_id));
  return card;
}

function renderList(id, tickets, makeCard) {
  if (tickets.length) { $(id).replaceChildren(...tickets.map(makeCard)); return; }
  $(id).replaceChildren(emptyState(id === "pending" ? "inbox" : "file-check", id === "pending" ? "暂无待处理申请" : "暂无处理记录", "", true));
}

function signOut() {
  signedIn = false;
  lastTickets = "";
  drafts.clear();
  setSignedIn(null);
}

async function refresh() {
  let data;
  try { data = await api("/api/review/tickets"); }
  catch (error) { if (error.status === 401) return signOut(); throw error; }
  const key = JSON.stringify(data);
  if (key === lastTickets) return;
  lastTickets = key;
  const active = document.activeElement;
  const focused = active && active.dataset.ticket;
  const start = focused ? active.selectionStart : 0;
  const end = focused ? active.selectionEnd : 0;
  $("pending-count").textContent = data.pending.length;
  $("decided-count").textContent = data.decided.length;
  renderList("pending", data.pending, pendingCard);
  renderList("decided", data.decided.slice().reverse(), decidedCard);
  if (focused) {
    const note = document.querySelector(`textarea[data-ticket="${CSS.escape(focused)}"]`);
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
  busy = true;
  for (const node of document.querySelectorAll("#pending button, #pending textarea")) node.disabled = true;
  showStatus("处理中…");
  try {
    const path = `/api/review/tickets/${encodeURIComponent(ticketId)}/decision`;
    const result = await api(path, { decision, note: drafts.get(ticketId) || "" });
    drafts.delete(ticketId);
    showStatus(`${ticketId} · ${STATUS_TEXT[result.ticket.status]}`);
    showTab(decision === "request_info" ? "pending" : "decided");
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
    showTab("pending");
    showStatus("已清空演示记录");
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
  $("tab-pending").addEventListener("click", () => showTab("pending"));
  $("tab-decided").addEventListener("click", () => showTab("decided"));
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
  startPolling(() => (signedIn && !busy ? refresh() : null), 3000);
}

boot().catch((error) => {
  showStatus(error.message, true);
  $("login").hidden = false;
  $("login-choices").replaceChildren(el("p", "status error", error.message));
});
