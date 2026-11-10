"use strict";

const QUICK = [
  ["晚到 50 分钟", "ORD001"], ["恰好 30 分钟", "ORD003"], ["30 分 1 秒", "ORD005"],
  ["未提供订单号", "我的外卖迟到了，可以申请补偿吗？"], ["其他账号的订单", "ORD101"], ["查无订单", "ORD999"],
];
const ORDER_STATUS = { delivered: "已送达", delivering: "配送中" };
let signedIn = false;
let busy = false;
let confirming = false;
let lastState = "";
let lastMessages = "";
let orders = [];
let expandedOrders = false;
const informationDrafts = new Map();

function updateControls() {
  const locked = busy || confirming;
  for (const node of document.querySelectorAll("#composer textarea, #composer button, #quick button, #orders button, #tickets textarea, #tickets button, .suggestion")) node.disabled = locked;
  $("confirm-yes").disabled = busy;
  $("confirm-no").disabled = busy;
  $("send").setAttribute("aria-busy", String(busy));
  document.body.classList.toggle("is-working", busy);
}

function renderMessages(messages) {
  const key = JSON.stringify(messages);
  if (key === lastMessages) return;
  lastMessages = key;
  const box = $("messages");
  if (!messages.length) {
    const welcome = el("div", "chat-welcome");
    welcome.append(careBuddy("buddy-welcome"), el("h3", "", "想处理哪笔订单？"));
    const suggestions = el("div", "suggestion-row");
    for (const [label, text] of [["ORD001 晚到了", "我的外卖 ORD001 迟到了，可以申请补偿吗？"], ["咨询延误补偿", "我的外卖迟到了，可以申请补偿吗？"]]) {
      const suggestion = button(label, "suggestion", () => send(text));
      suggestion.append(icon("arrow-up-right"));
      suggestions.append(suggestion);
    }
    welcome.append(suggestions);
    box.replaceChildren(welcome);
    return;
  }
  box.replaceChildren(...messages.map((item) => {
    if (item.role === "tool") {
      const line = el("p", "tool-line");
      line.append(icon("search"), el("span", "", item.text.replace("查单工具 query_order：", "查询 ")));
      return line;
    }
    const row = el("div", `bubble-row ${item.role}`);
    row.append(el("div", "bubble", item.text));
    return row;
  }));
  box.scrollTop = box.scrollHeight;
}

function renderConfirmation(claim) {
  confirming = Boolean(claim);
  $("confirm").hidden = !claim;
  if (claim) {
    $("confirm-facts").replaceChildren(...factRows([
      ["订单", claim.order_id], ["预计送达", claim.expected_at], ["实际送达", claim.delivered_at],
      ["晚到", delayText(claim.late_seconds)],
    ]));
    $("confirm-amount").replaceChildren(el("small", "", "补偿券"), document.createTextNode(`¥${claim.proposed_coupon_yuan}`));
  }
  updateControls();
}

function renderJourney(state) {
  let current = 0;
  if (state.confirmation) current = 1;
  else if (state.tickets.length) current = ["pending", "needs_info"].includes(state.tickets[state.tickets.length - 1].status) ? 2 : 3;
  const needsInfo = state.tickets.some((ticket) => ticket.status === "needs_info");
  $("journey").children[2].querySelector("strong").textContent = needsInfo ? "补充说明" : "人工审核";
  [...$("journey").children].forEach((node, index) => {
    node.classList.toggle("current", index === current);
    node.classList.toggle("done", index < current);
    if (index === current) node.setAttribute("aria-current", "step");
    else node.removeAttribute("aria-current");
  });
}

function renderTickets(tickets) {
  const active = document.activeElement;
  const focusedId = active && active.matches("textarea[data-information]") ? active.closest("[data-ticket-id]").dataset.ticketId : null;
  const selection = focusedId ? [active.selectionStart, active.selectionEnd] : null;
  const currentIds = new Set(tickets.filter((ticket) => ticket.status === "needs_info").map((ticket) => ticket.ticket_id));
  for (const id of informationDrafts.keys()) if (!currentIds.has(id)) informationDrafts.delete(id);
  if (!tickets.length) {
    openHistories.clear();
    $("tickets").replaceChildren(emptyState("ticket", "暂无申请"));
    return;
  }
  $("tickets").replaceChildren(...tickets.slice().reverse().map((ticket) => {
    const card = el("article", `ticket ticket-${ticket.status}`);
    card.dataset.ticketId = ticket.ticket_id;
    const head = el("div", "ticket-head");
    const heading = el("strong", "", ticket.order_id);
    heading.append(el("small", "", ticket.ticket_id));
    head.append(heading, badge(ticket.status));
    const highlight = el("div", "ticket-highlight");
    const text = el("div");
    const approved = ticket.status === "approved";
    text.append(el("h3", "", approved ? "已到账 · 补偿券" : "申请补偿券"),
      el("strong", "result-amount", `¥${approved ? ticket.coupon_issued_yuan : ticket.proposed_coupon_yuan}`));
    if (ticket.status === "pending") text.append(el("p", "", "等待商家审核"));
    else if (ticket.status === "rejected") text.append(el("p", "", "本次未发放"));
    highlight.append(text, icon(ticket.status === "pending" ? "clock" : approved ? "check" : "close"));
    card.append(head, highlight, facts([
      ["预计送达", ticket.expected_at], ["实际送达", ticket.delivered_at],
      ["晚到", delayText(ticket.late_seconds)],
    ]));
    const timeline = el("ol", "mini-timeline");
    const complete = !["pending", "needs_info"].includes(ticket.status);
    ["已提交", "审核", "结果"].forEach((label, index) => {
      timeline.append(el("li", complete ? (index === 2 ? "current" : "done") : (index === 0 ? "done" : index === 1 ? "current" : ""), label));
    });
    card.append(timeline);
    if (ticket.status === "needs_info") {
      const request = el("div", "information-request");
      request.append(el("span", "", "请补充"), el("p", "", ticket.information_request));
      const form = el("form", "information-form");
      const inputId = `ticket-information-${ticket.ticket_id}`;
      const label = el("label", "note-label", "补充说明");
      label.htmlFor = inputId;
      const input = el("textarea", "note");
      input.id = inputId;
      input.dataset.information = "";
      input.rows = 3;
      input.maxLength = 500;
      input.required = true;
      input.placeholder = "填写需要补充的信息";
      input.value = informationDrafts.get(ticket.ticket_id) || "";
      input.addEventListener("input", () => informationDrafts.set(ticket.ticket_id, input.value));
      const submit = el("button", "primary", "提交补充");
      submit.type = "submit";
      submit.dataset.action = "submit-information";
      form.append(label, input, submit);
      form.addEventListener("submit", (event) => {
        event.preventDefault();
        const text = input.value.trim();
        if (busy || confirming) return;
        if (!text) { input.focus(); showStatus("请填写补充说明", true); return; }
        act(async () => {
          await api(`/api/customer/tickets/${encodeURIComponent(ticket.ticket_id)}/information`, { text });
          informationDrafts.delete(ticket.ticket_id);
        });
      });
      card.append(request, form);
    } else if (ticket.review_note) {
      const note = el("div", "ticket-note");
      note.append(el("span", "", "商家回复"), el("p", "", ticket.review_note));
      card.append(note);
    }
    if (ticket.customer_information) {
      const information = el("div", "customer-information");
      information.append(el("span", "", "你的补充"), el("p", "", ticket.customer_information));
      card.append(information);
    }
    card.append(ticketHistory(ticket.ticket_id));
    return card;
  }));
  if (focusedId) {
    const input = $("tickets").querySelector(`[data-ticket-id="${CSS.escape(focusedId)}"] textarea[data-information]`);
    if (input && !input.disabled) { input.focus({ preventScroll: true }); input.setSelectionRange(...selection); }
  }
  updateControls();
}

function renderOrders() {
  const query = $("order-search").value.trim().toLowerCase();
  const matching = orders.filter((order) => `${order.order_id} ${order.merchant}`.toLowerCase().includes(query));
  const shown = query || expandedOrders ? matching : matching.slice(0, 3);
  $("orders").replaceChildren(...shown.map((order) => {
    const row = el("div", "order");
    const text = el("div", "order-text");
    text.append(el("strong", "", order.merchant), el("span", "order-meta", `${order.order_id} · ${ORDER_STATUS[order.status] || order.status}`));
    const bottom = el("div", "order-bottom");
    const time = order.delivered_at ? `${order.expected_at} → ${order.delivered_at}` : `预计 ${order.expected_at}`;
    bottom.append(el("span", "order-time", time), button("咨询", "small", () => send(`我的外卖 ${order.order_id} 迟到了，可以申请补偿吗？`)));
    text.append(bottom);
    row.append(icon("bowl", "order-art"), text);
    return row;
  }));
  if (!matching.length) $("orders").append(el("p", "empty search-empty", "未找到订单"));
  $("more-orders").hidden = Boolean(query) || matching.length <= 3;
  $("more-orders").replaceChildren(el("span", "", expandedOrders ? "收起" : `全部订单 · ${matching.length}`), icon("chevron-down"));
  $("more-orders").setAttribute("aria-expanded", String(expandedOrders));
  updateControls();
}

function signOut() {
  informationDrafts.clear();
  signedIn = false;
  lastState = "";
  lastMessages = "";
  setSignedIn(null);
}

async function refresh() {
  let state;
  try { state = await api("/api/customer/state"); }
  catch (error) { if (error.status === 401) return signOut(); throw error; }
  const key = JSON.stringify(state);
  if (key === lastState) return;
  lastState = key;
  renderMessages(state.messages);
  renderConfirmation(state.confirmation);
  renderTickets(state.tickets);
  renderJourney(state);
}

async function act(work) {
  if (busy) return;
  busy = true;
  updateControls();
  showStatus("处理中…");
  try { await work(); showStatus(""); }
  catch (error) { showStatus(error.message, true); }
  finally {
    busy = false;
    await refresh().catch((error) => showStatus(error.message, true));
    updateControls();
  }
}

function send(raw, fromInput) {
  const text = raw.trim();
  if (!text || confirming) return;
  act(async () => {
    await api("/api/customer/messages", { text });
    if (fromInput) { $("input").value = ""; updateCount(); }
  });
}

function updateCount() { $("input-count").textContent = `${$("input").value.length} / 500`; }

async function enter(customer) {
  informationDrafts.clear();
  orders = (await api("/api/customer/orders")).orders;
  expandedOrders = false;
  $("order-search").value = "";
  lastState = "";
  lastMessages = "";
  renderOrders();
  await refresh();
  signedIn = true;
  setSignedIn(customer.display_name);
}

async function boot() {
  const info = await api("/api/health");
  renderMeta(info);
  renderLogin(info.customers, "customer_id", async (customerId) => {
    try { await enter((await api("/api/customer/login", { customer_id: customerId })).customer); }
    catch (error) { showStatus(error.message, true); }
  });
  $("quick").replaceChildren(...QUICK.map(([label, text]) => button(label, "suggestion", () => { $("demo-dialog").close(); send(text); })));
  $("composer").addEventListener("submit", (event) => { event.preventDefault(); send($("input").value, true); });
  $("input").addEventListener("input", updateCount);
  $("input").addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey && !event.isComposing) { event.preventDefault(); send($("input").value, true); }
  });
  $("order-search").addEventListener("input", renderOrders);
  $("more-orders").addEventListener("click", () => { expandedOrders = !expandedOrders; renderOrders(); });
  $("confirm-yes").addEventListener("click", () => act(() => api("/api/customer/confirm", { answer: "confirm" })));
  $("confirm-no").addEventListener("click", () => act(() => api("/api/customer/confirm", { answer: "cancel" })));
  $("logout").addEventListener("click", async () => {
    if (busy) return;
    try { await api("/api/customer/logout", {}); signOut(); showStatus(""); }
    catch (error) { showStatus(error.message, true); }
  });
  try { await enter((await api("/api/customer/me")).customer); }
  catch (error) { if (error.status !== 401) throw error; signOut(); }
  startPolling(() => (signedIn && !busy ? refresh() : null), 3000);
}

boot().catch((error) => {
  showStatus(error.message, true);
  $("login").hidden = false;
  $("login-choices").replaceChildren(el("p", "status error", error.message));
});
