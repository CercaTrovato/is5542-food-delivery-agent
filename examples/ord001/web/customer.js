"use strict";

const QUICK = [
  ["P01 晚到50分钟（可赔）", "我的外卖 ORD001 迟到了，可以申请补偿吗？"],
  ["P02 晚到10分钟（拒赔）", "我的外卖 ORD002 迟到了，可以申请补偿吗？"],
  ["边界 恰好30:00（拒赔）", "我的外卖 ORD003 迟到了，可以申请补偿吗？"],
  ["边界 29分59秒（拒赔）", "我的外卖 ORD004 迟到了，可以申请补偿吗？"],
  ["边界 30分01秒（可赔）", "我的外卖 ORD005 迟到了，可以申请补偿吗？"],
  ["配送中盯盘（ORD006）", "帮我查一下 ORD006 送到哪了"],
  ["缺送达记录（ORD007）", "ORD007 怎么没有送达时间，能赔吗？"],
  ["餐品异物/有蟑螂（智能分流）", "我ordoo6的餐食有蟑螂，需要申请赔付"],
  ["P03 查他人订单（ORD101）", "帮我查一下 ORD101"],
  ["P03 查无此单（ORD999）", "ORD999 迟到了能赔吗"],
  ["未提供订单号", "我的外卖迟到了，可以申请补偿吗？"],
  ["转人工客服", "我想找人工客服"],
];
const ORDER_STATUS = { delivered: "已送达", delivering: "配送中" };
const HANDOFF_NOTE = { waiting: "已转人工，排队中，人工客服会在这里回复", replied: "人工客服已接入", cancelled: "已取消转人工" };
let signedIn = false;
let busy = false;
let confirming = false;
let lastState = "";
let lastChat = "";
let orders = [];
let expandedOrders = false;
let expandedPicks = false;
let plusOpen = false;
let policy = null;
let latest = null;
let lastFocus = null;
let viewTicket = null;
let shownOrder = null;
let othersOpen = null;
let handoffWaiting = false;
let seen = null;
let toastTimer = 0;
let draftMedia = null;
let pendingUserText = "";
let recorder = null;
let recorderStream = null;
let recorderChunks = [];
let recorderTimer = 0;
let recorderStartedAt = 0;
const informationDrafts = new Map();
const MAX_MEDIA_BYTES = 5 * 1024 * 1024;
const IMAGE_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

const FOOD_EMOJI_MAP = [
  [/牛肉|牛腩|牛排/, "🥩"],
  [/鸡|乳鸽|鸡翅/, "🍗"],
  [/烧肉|叉烧|猪扒/, "🍖"],
  [/云吞|虾|面/, "🍜"],
  [/柠茶|奶茶|气泡水|饮料/, "🧋"],
  [/汤/, "🍲"],
];

function foodEmoji(name) {
  for (const [re, emoji] of FOOD_EMOJI_MAP) {
    if (re.test(name)) return emoji;
  }
  return "🍱";
}

function updateControls() {
  const locked = busy || confirming;
  for (const node of document.querySelectorAll("#composer textarea, #composer button, #quick button, #orders button, #order-picks button, #tickets textarea, #tickets button, .suggestion, .im-tray-tile, #open-order-sheet")) node.disabled = locked;
  for (const node of document.querySelectorAll("#confirm-yes, #confirm-no, .handoff-cancel")) node.disabled = busy;
  $("attachment-input").disabled = locked || Boolean(recorder);
  $("attach").disabled = locked || Boolean(recorder);
  $("send").disabled = locked || Boolean(recorder);
  $("record").disabled = locked;
  if ($("tray-record")) $("tray-record").disabled = locked;
  $("handoff").disabled = busy || handoffWaiting;
  $("send").setAttribute("aria-busy", String(busy));
  document.body.classList.toggle("is-working", busy);
}

function toast(text) {
  const node = $("toast");
  node.replaceChildren(icon("bell"), el("span", "", text));
  node.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => node.classList.remove("show"), 6000);
}

function bubble(role, text, tag) {
  const row = el("div", `bubble-row ${role}`);
  if (role === "assistant" || role === "human") {
    const head = el("div", "bubble-sender-head");
    const avatar = document.createElement("img");
    avatar.className = "bubble-avatar-img";
    if (role === "human") {
      avatar.src = "/static/chubby-joker.png";
      avatar.alt = "人工客服 Joker";
    } else {
      const item = currentMjItem();
      avatar.src = item.src;
      avatar.dataset.mascot = "mj";
      avatar.dataset.headItem = item.key;
      avatar.alt = "AI 客服 MJ";
    }
    head.append(
      avatar,
      el("span", "bubble-tag", role === "human" ? "人工专员 · Joker" : (tag === "AI" ? "67餐厅 AI 客服 · MJ" : (tag || "MJ")))
    );
    row.append(head);
  } else if (tag) {
    row.append(el("span", "bubble-tag", tag));
  }
  row.append(el("div", "bubble", text));
  return row;
}

// Meituan Waimai style Rich Order Card rendered directly in the chat stream when an order is queried.
function chatOrderCard(order) {
  const card = el("article", "waimai-chat-card");
  const shopRow = el("div", "waimai-shop-row");
  const shopAvatar = mascotImg("waimai-shop-avatar");
  shopRow.append(shopAvatar, el("span", "waimai-shop-name", `${order.merchant}（港城店）`));
  if (order.case) {
    shopRow.append(el("span", "order-case-pill", order.case.replace(/^P0\d\s*/, "")));
  }
  const title = el("h4", "waimai-card-title", order.status === "delivering" ? "订单配送中 · 实时核验" : "已核实订单履约信息");
  const rawItems = Array.isArray(order.items) && order.items.length ? order.items : ["招牌黑椒厚切牛肉饭 ×1", "港式冻柠茶 ×1"];
  const gallery = el("div", "waimai-food-gallery");
  const thumbs = el("div", "waimai-food-thumbs");
  let totalCount = 0;
  for (const raw of rawItems) {
    const [dishName, qtyRaw] = String(raw).split(" ×");
    const qty = Number(qtyRaw) || 1;
    totalCount += qty;
    const foodItem = el("div", "waimai-food-item");
    const pic = el("div", "waimai-food-pic", foodEmoji(dishName));
    const caption = el("span", "waimai-food-name", dishName);
    foodItem.append(pic, caption);
    thumbs.append(foodItem);
  }
  const priceCol = el("div", "waimai-price-col");
  priceCol.append(el("strong", "", `¥${Number(order.amount_yuan).toFixed(1)}`), el("small", "", `共 ${totalCount} 件`));
  gallery.append(thumbs, priceCol);

  const meta = el("dl", "waimai-meta-grid");
  const timeVal = order.delivered_at
    ? `预计 ${order.expected_at} · 实际 ${order.delivered_at}`
    : (order.status === "delivering" ? `配送中（预计 ${order.expected_at} 送达）` : `预计 ${order.expected_at} · 暂缺签收记录`);
  const rows = [
    ["订单编号：", order.order_id],
    ["配送时间：", timeVal],
    ["履约说明：", order.liability_detail || order.liability_party || "系统已核实配送记录"],
  ];
  for (const [k, v] of rows) {
    meta.append(el("dt", "", k), el("dd", "", v));
  }

  const footBtn = button(
    order.status === "delivering" ? "订单配送中 · 查看实时详情" : "订单已完成 · 查看履约详情",
    "waimai-card-btn",
    () => showOrderDetail(order)
  );
  card.append(shopRow, title, gallery, meta, footBtn);
  return card;
}

function attachmentBubble(item) {
  const row = el("div", "bubble-row customer attachment-row");
  row.append(el("span", "bubble-tag", "顾客附件"), attachmentList(item.attachments, { customer: true }));
  return row;
}

function handoffBlock(item) {
  const nodes = [];
  if (item.request_text) nodes.push(bubble("customer", item.request_text));
  if (item.attachments && item.attachments.length) nodes.push(attachmentBubble(item));
  const note = el("div", `handoff-note note-${item.status}`);
  note.dataset.handoffId = item.handoff_id;
  note.append(icon(item.status === "cancelled" ? "close" : "person"), el("span", "", HANDOFF_NOTE[item.status] || item.status));
  if (item.status === "waiting") {
    note.append(button("取消", "handoff-cancel", () => act(() => api(`/api/customer/handoffs/${encodeURIComponent(item.handoff_id)}/cancel`, {}))));
  }
  nodes.push(note);
  if (item.status === "replied") nodes.push(bubble("human", item.reply_text, "人工客服"));
  return nodes;
}

function welcome() {
  const box = el("div", "chat-welcome");
  const hero = el("div", "welcome-hero");
  const copy = el("div", "welcome-copy");
  const badgeRow = el("div", "welcome-badge-row");
  badgeRow.append(
    el("span", "welcome-kicker", "AI 客服 MJ"),
    el("span", "welcome-kicker joker-kicker", "人工专员 Joker")
  );
  copy.append(
    badgeRow,
    el("h3", "", "嗨！我是 MJ，想咨询哪一笔外卖订单？"),
    el("p", "welcome-note", "点击下方「选择需要咨询的订单」或输入框右侧「+」号，即可像美团外卖一样弹出订单卡片一键发送；疑难食安问题由小丑人工专员优先跟进。")
  );
  const mascotPair = el("div", "welcome-mascot-pair");
  const jokerCard = el("div", "joker-side-badge");
  const jokerImg = document.createElement("img");
  jokerImg.src = "/static/chubby-joker.png";
  jokerImg.alt = "小丑专员";
  jokerCard.append(jokerImg, el("small", "", "Joker 专员"));
  mascotPair.append(careBuddy("buddy-welcome"), jokerCard);
  hero.append(mascotPair, copy);

  const openSheetBtn = button("📦 选择需要咨询的订单（共 " + (orders.length || 8) + " 笔）", "welcome-order-cta", () => openOrderSheet());
  const suggestions = el("div", "suggestion-row");
  suggestions.append(el("span", "suggestion-title", "猜你想问"));
  for (const [label, text] of [
    ["ORD001 晚到了", "我的外卖 ORD001 迟到了，可以申请补偿吗？"],
    ["ORD002 差多久达标", "我的外卖 ORD002 迟到了，可以申请补偿吗？"],
    ["ORD006 餐里有蟑螂", "我ordoo6的餐食有蟑螂，需要申请赔付"],
    ["未带单号咨询", "我的外卖迟到了，可以申请补偿吗？"],
  ]) {
    const suggestion = button(label, "suggestion", () => send(text));
    suggestion.append(icon("arrow-up-right"));
    suggestions.append(suggestion);
  }
  box.append(hero, openSheetBtn, suggestions);
  return box;
}

function typingBubble() {
  const row = el("div", "bubble-row assistant typing-row");
  const head = el("div", "bubble-sender-head");
  const avatar = mascotImg("bubble-avatar-img");
  head.append(avatar, el("span", "bubble-tag", "67餐厅 AI 客服 · MJ"));
  const bub = el("div", "bubble typing-bubble");
  bub.append(el("span", "typing-text", "MJ 正在核实订单并思考"), el("span", "typing-dots", "···"));
  row.append(head, bub);
  return row;
}

function renderMessages(messages, handoffs) {
  const key = JSON.stringify([messages, handoffs, pendingUserText, orders.length]);
  if (key === lastChat) return;
  lastChat = key;
  const box = $("messages");
  if (!messages.length && !handoffs.length && !pendingUserText) { box.replaceChildren(welcome()); updateControls(); return; }
  const nodes = [];
  // A handoff sits after the chat lines that existed when it was opened.
  const place = (index) => {
    for (const item of handoffs) if (Math.min(item.after, messages.length) === index) nodes.push(...handoffBlock(item));
  };
  messages.forEach((item, index) => {
    place(index);
    if (item.role === "tool") {
      const oid = item.text.replace("查单工具 query_order：", "").trim();
      const line = el("p", "tool-line");
      line.append(icon("search"), el("span", "", `已通过查单工具核实：${oid}`));
      nodes.push(line);
      const matchedOrder = orders.find((o) => o.order_id === oid);
      if (matchedOrder) {
        nodes.push(chatOrderCard(matchedOrder));
      }
    } else {
      nodes.push(bubble(item.role, item.text, item.role === "assistant" ? "AI" : ""));
      if (item.role === "assistant" && /提供订单号|选择.*订单|哪一?笔订单/.test(item.text)) {
        const promptBtn = button("📦 点击选择需要咨询的订单", "inline-order-sheet-btn", () => openOrderSheet());
        nodes.push(promptBtn);
      }
    }
  });
  place(messages.length);
  if (pendingUserText) {
    nodes.push(bubble("customer", pendingUserText, ""));
    nodes.push(typingBubble());
  }
  box.replaceChildren(...nodes);
  box.scrollTop = box.scrollHeight;
  updateControls();
}

function renderConfirmation(claim) {
  confirming = Boolean(claim);
  $("confirm").hidden = !claim;
  if (claim) {
    const rows = [
      ["订单", claim.order_id], ["预计送达", claim.expected_at], ["实际送达", claim.delivered_at],
      ["晚到", delayText(claim.late_seconds)],
    ];
    $("confirm-facts").replaceChildren(...factRows(rows));
    $("confirm-amount").replaceChildren(el("small", "", "补偿券"), document.createTextNode(`¥${claim.proposed_coupon_yuan}`));
  }
  updateControls();
}

function slaMeter(lateSeconds) {
  if (typeof lateSeconds !== "number" || lateSeconds < 0) return null;
  const threshold = (policy ? policy.threshold_minutes : 30) * 60;
  const pct = Math.min(100, Math.round((lateSeconds / (threshold * 1.8)) * 100));
  const eligible = policy && policy.include_threshold ? lateSeconds >= threshold : lateSeconds > threshold;
  const wrap = el("div", `sla-meter ${eligible ? "is-eligible" : "is-below"}`);
  const labels = el("div", "sla-labels");
  labels.append(
    el("span", "", "0m 准时"),
    el("span", "sla-threshold-mark", `${policy ? policy.threshold_minutes : 30}m 起赔线`),
    el("span", "", eligible ? "已达标 · ¥10" : "容差免赔区")
  );
  const track = el("div", "sla-track");
  const fill = el("div", "sla-fill");
  fill.style.width = `${ Math.max(6, pct) }%`;
  const marker = el("span", "sla-line");
  track.append(fill, marker);
  wrap.append(labels, track);
  return wrap;
}

function ruleText() {
  if (!policy) return "达到晚到条件";
  return policy.include_threshold ? `晚到 ${policy.threshold_minutes} 分钟及以上` : `晚到超过 ${policy.threshold_minutes} 分钟`;
}

function renderJourney(state, ticket) {
  let current = 0;
  if (state.confirmation) current = 1;
  else if (ticket) current = ["pending", "needs_info"].includes(ticket.status) ? 2 : 3;
  $("journey").children[2].querySelector("strong").textContent = ticket && ticket.status === "needs_info" ? "补充说明" : "人工审核";
  [...$("journey").children].forEach((node, index) => {
    node.classList.toggle("current", index === current);
    node.classList.toggle("done", index < current);
    if (index === current) node.setAttribute("aria-current", "step");
    else node.removeAttribute("aria-current");
  });
}

function ratingBlock(ticket) {
  const box = el("div", "rating");
  if (ticket.rating) {
    box.classList.add("rated");
    const stars = el("span", "rating-done");
    for (let n = 1; n <= 5; n += 1) stars.append(icon("star", n <= ticket.rating ? "star-on" : "star-off"));
    box.append(el("span", "rating-label", "你的评价"), stars, el("span", "rating-score", `${ticket.rating} 分 · 谢谢反馈`));
    return box;
  }
  box.append(el("span", "rating-label", "这次处理满意吗？"));
  const stars = el("div", "rating-stars");
  for (let n = 1; n <= 5; n += 1) {
    const star = button("", "rate-star", () => act(() => api(`/api/customer/tickets/${encodeURIComponent(ticket.ticket_id)}/rating`, { rating: n })));
    star.setAttribute("aria-label", `${n} 分`);
    star.append(icon("star"));
    stars.append(star);
  }
  box.append(stars);
  return box;
}

function informationForm(ticket) {
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
  return [request, form];
}

function ticketCard(ticket) {
  const order = orders.find((item) => item.order_id === ticket.order_id) || ticket;
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
  if (ticket.status === "pending") text.append(el("p", "", "等待商家审核，预计 24 小时内处理"));
  else if (ticket.status === "rejected") text.append(el("p", "", "本次未发放"));
  highlight.append(text, icon("spidey"));
  card.append(head, highlight);
  const chain = fulfillmentChain(order);
  if (chain) card.append(chain);
  card.append(facts([
    ["预计送达", ticket.expected_at], ["实际送达", ticket.delivered_at],
    ["晚到", delayText(ticket.late_seconds)],
  ]));
  const attr = attributionBox(order);
  if (attr) card.append(attr);
  const timeline = el("ol", "mini-timeline");
  const complete = !["pending", "needs_info"].includes(ticket.status);
  ["已提交", "审核", "结果"].forEach((label, index) => {
    timeline.append(el("li", complete ? (index === 2 ? "current" : "done") : (index === 0 ? "done" : index === 1 ? "current" : ""), label));
  });
  card.append(timeline);
  if (ticket.status === "needs_info") card.append(...informationForm(ticket));
  else if (ticket.review_note) {
    const note = el("div", "ticket-note");
    note.append(el("span", "", "商家回复"), el("p", "", ticket.review_note));
    card.append(note);
  }
  if (ticket.customer_information) {
    const information = el("div", "customer-information");
    information.append(el("span", "", "你的补充"), el("p", "", ticket.customer_information));
    card.append(information);
  }
  if (complete) card.append(ratingBlock(ticket));
  card.append(ticketHistory(ticket.ticket_id));
  return card;
}

// The order the chat is about, before any ticket exists: what the rule says and what to do next.
function stateCard(focus, claim) {
  const order = orders.find((item) => item.order_id === focus.order_id);
  const card = el("article", "focus-card");
  card.dataset.focusOrder = focus.order_id;
  const head = el("div", "ticket-head");
  const heading = el("strong", "", focus.order_id);
  if (order) heading.append(el("small", "", `${order.merchant} · 实付 ¥${order.amount_yuan}`));
  head.append(heading);
  const highlight = el("div", "ticket-highlight");
  const text = el("div");
  let kind, title, note, amount = null, symbol = "info", action = null;
  if (!focus.verified) {
    kind = "unverified"; title = "无法核实这笔订单"; note = "当前账号下没有这笔订单。请核对订单号，或从「我的订单」中选择。";
  } else if (claim) {
    kind = "confirm"; title = "待你确认"; amount = claim.proposed_coupon_yuan; symbol = "file-check"; note = "核对对话框里的信息后点「确认提交」";
  } else if (focus.status === "pending") {
    kind = "eligible"; title = "符合申请条件"; amount = focus.proposed_coupon_yuan; symbol = "ticket"; note = "提交后由商家人工审核";
    action = button("申请补偿", "primary", () => send(`我的外卖 ${focus.order_id} 迟到了，可以申请补偿吗？`));
  } else if (focus.reason_code === "delay_below_threshold") {
    const late = focus.late_seconds > 0 ? `晚到 ${delayText(focus.late_seconds)}` : "没有晚到";
    kind = "ineligible"; title = "未达到申请条件"; note = `本单${late}；需${ruleText()}才能申请。`;
  } else if (focus.reason_code === "not_delivered") {
    kind = "delivering"; title = "订单还在配送中"; symbol = "clock"; note = `送达后如${ruleText()}，可以再来申请。`;
  } else {
    kind = "unknown"; title = "暂缺送达记录"; note = "系统无法判断是否晚到。需要的话可以点「转人工」。";
  }
  card.classList.add(`focus-${kind}`);
  text.append(el("h3", "", title));
  if (amount !== null) text.append(el("strong", "result-amount", `¥${amount}`));
  text.append(el("p", "", note));
  highlight.append(text, icon("spidey"));
  card.append(head, highlight);
  if (focus.verified && order) {
    const chain = fulfillmentChain(order);
    if (chain) card.append(chain);
    const meter = slaMeter(focus.late_seconds);
    if (meter) card.append(meter);
    card.append(facts([
      ["预计送达", order.expected_at], ["实际送达", order.delivered_at || "未送达"],
      ["晚到", focus.late_seconds === null || focus.late_seconds === undefined ? "—" : delayText(focus.late_seconds)],
    ]));
    const attr = attributionBox(order);
    if (attr) card.append(attr);
    if (focus.reason_code === "not_delivered") {
      const radar = el("div", "rider-radar");
      const headRow = el("div", "radar-head");
      headRow.append(el("span", "radar-pulse"), el("strong", "", `骑手实时雷达 · 距您约 ${order.rider_distance_m || 380}m`));
      const sub = el("p", "", `预计 ${order.rider_eta_min || 3} 分钟内送达；送达后系统将自动计算准时保差值。`);
      const urgeBtn = button("一键催单并开启自动盯盘", "secondary urge-button", () => {
        toast(`${order.order_id} 已向骑手发送优先催单提醒，送达后将自动核验准时保`);
      });
      radar.append(headRow, sub, urgeBtn);
      card.append(radar);
    }
  }
  if (action) { action.append(icon("arrow-right")); card.append(action); }
  return card;
}

function focusHint() {
  const box = el("div", "focus-hint");
  box.append(icon("search"), el("p", "", "在对话里发订单号，或点「我的订单」里的「咨询」，这里会显示那笔订单的进度。"));
  return box;
}

function renderTickets(state, ticket) {
  const active = document.activeElement;
  const focusedId = active && active.matches("textarea[data-information]") ? active.closest("[data-ticket-id]").dataset.ticketId : null;
  const selection = focusedId ? [active.selectionStart, active.selectionEnd] : null;
  const currentIds = new Set(state.tickets.filter((item) => item.status === "needs_info").map((item) => item.ticket_id));
  for (const id of informationDrafts.keys()) if (!currentIds.has(id)) informationDrafts.delete(id);
  if (ticket) $("tickets").replaceChildren(ticketCard(ticket));
  else if (state.focus) $("tickets").replaceChildren(stateCard(state.focus, state.confirmation));
  else if (state.tickets.length) $("tickets").replaceChildren(focusHint());
  else { openHistories.clear(); $("tickets").replaceChildren(emptyState("ticket", "暂无申请")); }
  if (focusedId) {
    const input = $("tickets").querySelector(`[data-ticket-id="${CSS.escape(focusedId)}"] textarea[data-information]`);
    if (input && !input.disabled) { input.focus({ preventScroll: true }); input.setSelectionRange(...selection); }
  }
  updateControls();
}

// Every other application stays one tap away, without status badges that could be mistaken for the shown one.
function renderOthers(state, ticket) {
  const box = $("ticket-others");
  const rest = state.tickets.filter((item) => !ticket || item.ticket_id !== ticket.ticket_id).reverse();
  const back = Boolean(viewTicket && (!state.focus || !ticket || ticket.order_id !== state.focus.order_id));
  box.hidden = !rest.length && !back;
  const nodes = [];
  if (back) {
    const label = state.focus ? `回到当前咨询 · ${state.focus.order_id}` : "返回申请列表";
    const node = button(label, "back-focus", () => { viewTicket = null; renderPanel(); });
    node.prepend(icon(state.focus ? "chat" : "chevron-down"));
    nodes.push(node);
  }
  if (rest.length) {
    const details = el("details", "other-tickets");
    details.open = othersOpen ?? (!ticket && !state.focus);
    const summary = el("summary", "history-summary", `${ticket || state.focus ? "其他申请" : "我的申请"} · ${rest.length}`);
    summary.addEventListener("click", () => { othersOpen = !details.open; });
    summary.append(icon("chevron-down"));
    const list = el("div", "other-list");
    for (const item of rest) {
      const row = button("", "other-ticket", () => { viewTicket = item.ticket_id; renderPanel(); });
      row.append(el("strong", "", item.order_id),
        el("span", `mini-status status-${item.status}`, STATUS_TEXT[item.status] || item.status),
        el("span", "other-amount", `¥${item.status === "approved" ? item.coupon_issued_yuan : item.proposed_coupon_yuan}`));
      list.append(row);
    }
    details.append(summary, list);
    nodes.push(details);
  }
  box.replaceChildren(...nodes);
}

function markOrders() {
  for (const row of $("orders").querySelectorAll(".order")) row.classList.toggle("is-focus", row.dataset.orderId === shownOrder);
}

function showOrderDetail(order) {
  const root = $("order-detail");
  const defaultItems = ["招牌黑椒厚切牛肉饭 ×1", "港式冻柠茶 ×1"];
  const items = Array.isArray(order.items) && order.items.length ? order.items : defaultItems;
  const status = ORDER_STATUS[order.status] || order.status;
  root.replaceChildren();
  const heading = el("div", "order-detail-heading");
  const title = el("h2", "", "订单详情");
  title.id = "order-dialog-title";
  heading.append(el("span", "order-detail-kicker", "配送关怀 · 模拟订单"), title,
    el("span", "order-detail-status", status));
  const hero = el("div", "order-detail-hero");
  hero.append(el("span", "order-detail-merchant", order.merchant), el("strong", "", order.order_id),
    el("small", "", `实付 ¥${order.amount_yuan}`));
  const chain = fulfillmentChain(order);
  const attr = attributionBox(order);
  const itemList = el("div", "order-detail-items");
  for (const [index, rawName] of items.entries()) {
    const parts = String(rawName).split(" ×");
    const row = el("div", "order-detail-item");
    row.append(el("span", "food-thumb", index === 0 ? "主餐" : "配餐"), el("span", "", parts[0]), el("strong", "", parts[1] ? `×${parts[1]}` : "×1"));
    itemList.append(row);
  }
  const rows = [
    ["订单状态", status], ["实付金额", `¥${order.amount_yuan}`],
    ["下单时间", order.ordered_at || "17:20"], ["商家出餐", order.prep_done_at ? `${order.prep_done_at}（应出餐 ${order.prep_promised_at || "17:35"}）` : "—"],
    ["骑手取餐", order.picked_up_at || "—"], ["预计送达", order.expected_at],
    ["实际送达", order.delivered_at || (order.status === "delivering" ? "配送中" : "暂缺记录")],
  ];
  root.append(heading, hero);
  if (chain) root.append(chain);
  if (attr) root.append(attr);
  root.append(
    el("h3", "order-detail-section", "餐品明细"), itemList,
    el("h3", "order-detail-section", "配送信息"), facts(rows),
    el("p", "order-detail-note", "演示订单 · 账单与配送时间仅供测试。")
  );
  $("order-dialog").showModal();
}

function clearDraftMedia() {
  if (draftMedia && draftMedia.url) URL.revokeObjectURL(draftMedia.url);
  draftMedia = null;
  renderDraftMedia();
}

function renderDraftMedia() {
  const box = $("attachment-draft");
  if (!draftMedia) { box.hidden = true; box.replaceChildren(); updateControls(); return; }
  box.hidden = false;
  const label = draftMedia.kind === "image" ? "图片待发送" : "语音待发送";
  const row = el("div", "draft-media-row");
  row.append(icon(draftMedia.kind === "image" ? "image" : "audio"), el("strong", "", label),
    el("small", "", `${draftMedia.file.name} · ${(draftMedia.file.size / 1024 / 1024).toFixed(1)} MB`));
  const remove = button("移除", "media-remove", clearDraftMedia);
  remove.prepend(icon("trash"));
  row.append(remove);
  if (draftMedia.kind === "image") {
    const preview = document.createElement("img");
    preview.src = draftMedia.url;
    preview.alt = "待发送图片预览";
    row.append(preview);
  } else {
    const player = document.createElement("audio");
    player.controls = true;
    player.src = draftMedia.url;
    row.append(player);
  }
  box.replaceChildren(row);
  updateControls();
}

function setDraftMedia(file, kind) {
  if (!file || file.size > MAX_MEDIA_BYTES) {
    showStatus("附件不能超过 5 MB，请换一份较小的文件。", true);
    return false;
  }
  if (kind === "image" && !IMAGE_TYPES.has(file.type)) {
    showStatus("只支持 JPG、PNG 或 WebP 图片。", true);
    return false;
  }
  clearDraftMedia();
  draftMedia = { file, kind, url: URL.createObjectURL(file) };
  renderDraftMedia();
  showStatus(kind === "image" ? "图片已准备好，发送后会交给人工客服。" : "语音已准备好，发送后会交给人工客服。", false);
  return true;
}

function formatRecordingTime() {
  const seconds = Math.floor((Date.now() - recorderStartedAt) / 1000);
  return `录音中 ${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}

// The timer writes into #record-label, so every redraw of the button keeps that id.
function showRecordButton(recording) {
  const label = el("span", recording ? "record-time-pill" : "sr-only", recording ? formatRecordingTime() : "语音");
  label.id = "record-label";
  $("record").replaceChildren(icon(recording ? "stop" : "audio"), label);
  $("record").classList.toggle("recording", recording);
  $("record").setAttribute("aria-label", recording ? "停止录音" : "录制语音");
}

function stopRecording() {
  if (!recorder) return;
  recorder.stop();
  for (const track of recorderStream?.getTracks() || []) track.stop();
  clearInterval(recorderTimer);
  recorderTimer = 0;
  showRecordButton(false);
  updateControls();
}

async function toggleRecording() {
  if (recorder) { stopRecording(); return; }
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
    showStatus("当前浏览器不支持录音，请选择图片或点「转人工」留言。", true);
    return;
  }
  try {
    recorderStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const options = MediaRecorder.isTypeSupported("audio/webm;codecs=opus") ? { mimeType: "audio/webm;codecs=opus" } : {};
    recorderChunks = [];
    recorder = new MediaRecorder(recorderStream, options);
    recorder.addEventListener("dataavailable", event => { if (event.data.size) recorderChunks.push(event.data); });
    recorder.addEventListener("stop", () => {
      const type = recorder?.mimeType || "audio/webm";
      const file = new File([new Blob(recorderChunks, { type })], `语音-${Date.now()}.webm`, { type });
      recorder = null;
      recorderStream = null;
      recorderChunks = [];
      if (file.size) setDraftMedia(file, "audio");
      updateControls();
    }, { once: true });
    recorder.start();
    recorderStartedAt = Date.now();
    showRecordButton(true);
    recorderTimer = setInterval(() => { $("record-label").textContent = formatRecordingTime(); }, 1000);
    updateControls();
  } catch (_) {
    for (const track of recorderStream?.getTracks() || []) track.stop();
    recorder = null;
    recorderStream = null;
    showStatus("没有获得麦克风权限，录音未开始。", true);
    updateControls();
  }
}

function setPlusTray(open) {
  plusOpen = Boolean(open);
  const tray = $("plus-tray");
  const btn = $("plus-toggle");
  if (tray) tray.hidden = !plusOpen;
  if (btn) {
    btn.classList.toggle("is-open", plusOpen);
    btn.setAttribute("aria-expanded", String(plusOpen));
  }
}

function pickOrderAction(order) {
  switchMjByOrder(order.order_id);
  expandedPicks = false;
  setPlusTray(false);
  const sheet = $("order-sheet-dialog");
  if (sheet && sheet.open) sheet.close();
  const draft = $("input").value.trim();
  if (draft && !/ORD[\s\-_]*[0-9OIL]+/i.test(draft)) {
    $("input").value = "";
    updateCount();
    send(`${order.order_id} ${draft}`);
    return;
  }
  if (order.status === "delivering") {
    send(`帮我查一下 ${order.order_id} 送到哪了`);
  } else {
    send(`我的外卖 ${order.order_id} 迟到了，可以申请补偿吗？`);
  }
}

function renderOrderSheet() {
  const list = $("order-sheet-list");
  if (!list) return;
  const state = latest;
  const activeId = state && state.focus && state.focus.verified ? state.focus.order_id : shownOrder;
  list.replaceChildren();

  if (!orders.length) {
    const empty = el("div", "sheet-empty");
    empty.append(el("strong", "", "暂无订单"), el("p", "", "当前账号下没有可咨询的订单"));
    list.append(empty);
    return;
  }

  for (const order of orders) {
    const card = el("article", `sheet-order-card${order.order_id === activeId ? " is-active" : ""}`);
    const top = el("div", "sheet-order-top");
    const shop = el("div", "sheet-order-shop");
    shop.append(icon("bowl", "sheet-shop-icon"), el("strong", "", `${order.merchant}（港城店）`), el("span", "sheet-order-id", order.order_id));
    const statusText = order.case ? order.case.replace(/^P0\d\s*/, "") : (ORDER_STATUS[order.status] || order.status);
    top.append(shop, el("span", "order-case-pill", statusText));

    const rawItems = Array.isArray(order.items) && order.items.length ? order.items : ["招牌套餐 ×1"];
    const gallery = el("div", "waimai-food-gallery");
    const thumbs = el("div", "waimai-food-thumbs");
    let totalQty = 0;
    for (const raw of rawItems) {
      const [dishName, qtyRaw] = String(raw).split(" ×");
      const qty = Number(qtyRaw) || 1;
      totalQty += qty;
      const foodItem = el("div", "waimai-food-item");
      foodItem.append(el("div", "waimai-food-pic", foodEmoji(dishName)), el("span", "waimai-food-name", dishName));
      thumbs.append(foodItem);
    }
    const priceCol = el("div", "waimai-price-col");
    priceCol.append(el("strong", "", `¥${Number(order.amount_yuan).toFixed(1)}`), el("small", "", `共 ${totalQty} 件`));
    gallery.append(thumbs, priceCol);

    const timeRow = el("div", "sheet-order-foot");
    const timeStr = order.delivered_at
      ? `预计 ${order.expected_at} → 实际 ${order.delivered_at}`
      : (order.status === "delivering" ? `配送中 · 预计 ${order.expected_at} 送达` : `预计 ${order.expected_at} · 暂缺签收时间`);
    const actBtns = el("div", "sheet-order-actions");
    actBtns.append(
      button("订单详情", "small secondary", () => { $("order-sheet-dialog").close(); showOrderDetail(order); }),
      button(order.order_id === activeId ? "重新发送此单" : "选择此单咨询", "small primary", () => pickOrderAction(order))
    );
    timeRow.append(el("span", "sheet-order-time", timeStr), actBtns);
    card.append(top, gallery, timeRow);
    list.append(card);
  }

  if (orders.length === 1 && orders[0].order_id === "ORD101") {
    const switchBtn = button("切换到顾客 01（查看 ORD001–ORD008 共 8 笔主测试单）", "welcome-order-cta", async () => {
      try {
        $("order-sheet-dialog").close();
        await enter((await api("/api/customer/login", { customer_id: "U001" })).customer);
      } catch (error) { showStatus(error.message, true); }
    });
    list.append(switchBtn);
  }
}

function openOrderSheet() {
  setPlusTray(false);
  renderOrderSheet();
  const dialog = $("order-sheet-dialog");
  if (dialog && !dialog.open) dialog.showModal();
}

// Clean, non-cramped Meituan Waimai style quick-action floating pills right above the input bar.
function renderPicks(state) {
  const box = $("order-picks");
  const show = !state.confirmation && orders.length > 0;
  box.hidden = !show;
  if (!show) { box.replaceChildren(); return; }
  const activeId = state.focus && state.focus.verified ? state.focus.order_id : shownOrder;

  const bar = el("div", "waimai-floating-pills");
  const orderPill = button(
    activeId ? `📦 当前：${activeId} · 切换订单` : `📦 选择订单 (${orders.length})`,
    `waimai-pill waimai-pill-primary${activeId ? " is-active" : ""}`,
    () => openOrderSheet()
  );
  const claimPill = button("⚡ 申请准时保", "waimai-pill", () => {
    const target = orders.find((o) => o.order_id === (activeId || "ORD001")) || orders[0];
    if (target) pickOrderAction(target);
  });
  const urgePill = button("📍 催单/查进度", "waimai-pill", () => {
    const delivering = orders.find((o) => o.status === "delivering") || orders[0];
    if (delivering) send(`帮我查一下 ${delivering.order_id} 送到哪了`);
  });
  const ratePill = button("🧠 5层链路透视", "waimai-pill", () => $("demo-dialog").showModal());
  bar.append(orderPill, claimPill, urgePill, ratePill);
  box.replaceChildren(bar);
}

// Live 5-Layer LangGraph Architecture Visualizer for classroom presentation.
function buildPipelineView(state, ticket) {
  const hasMsg = state && state.messages && state.messages.length > 0;
  const lastTool = hasMsg ? [...state.messages].reverse().find((m) => m.role === "tool") : null;
  const queriedOid = lastTool ? lastTool.text.replace("查单工具 query_order：", "").trim() : null;
  const isHandoff = state && state.handoffs && state.handoffs.some((h) => h.status === "waiting" || h.status === "replied");
  const isVerified = state && state.focus && state.focus.verified;
  const isUnverified = state && state.focus && state.focus.verified === false;
  const isConfirming = Boolean(state && state.confirmation);

  const steps = [
    {
      num: "L1",
      title: "前置意图与否定消歧 (wants_person)",
      desc: isHandoff ? "已命中人工/附件队列直达 (handoffs)" : (hasMsg ? "非转人工意图 / 否定词消歧放行 → 进入图1" : "待命：识别「转人工」与「不用转人工」"),
      state: isHandoff ? "active-warn" : (hasMsg ? "done" : "idle"),
    },
    {
      num: "L2",
      title: "图1 · agent 节点 (DeepSeek + 模糊单号纠错)",
      desc: queriedOid ? `已归一并调用 query_order(${queriedOid})` : (hasMsg ? "自由对话理解 + 注入只读工单摘要" : "待命：提取单号 (如 ordoo6 → ORD006)"),
      state: queriedOid || (hasMsg && !isHandoff) ? "done" : "idle",
    },
    {
      num: "L3",
      title: "tools + assess (零信任鉴权 + 秒级精算 + 二次合成)",
      desc: isUnverified
        ? `零信任拦截：非本人或未知订单 (${state.focus.order_id})`
        : (isVerified
          ? `已核实 ${state.focus.order_id} (${state.focus.reason_code || "已评估"}) + DeepSeek 二次合成`
          : "待命：ToolRuntime 鉴权 + evaluate_order 算时"),
      state: isUnverified ? "active-warn" : (isVerified ? "done" : "idle"),
    },
    {
      num: "L4",
      title: "后置防幻觉风控护栏 (reply_risk)",
      desc: hasMsg ? "实时扫描通过：无越权金额 / 无虚假退款承诺" : "待命：拦截未授权金额、保证通过与虚假打款",
      state: hasMsg && !isHandoff ? "done" : "idle",
    },
    {
      num: "L5",
      title: "双状态机闭环 (confirm Interrupt → review_graph)",
      desc: isConfirming
        ? `confirm 节点 interrupt() 挂起：等待顾客确认 ${state.confirmation.order_id}`
        : (ticket
          ? `图2 review-${ticket.ticket_id}：${STATUS_TEXT[ticket.status] || ticket.status}${ticket.rating ? ` · 已评 ${ticket.rating}★` : ""}`
          : "待命：达标(>30m)触发顾客确认卡与商家审批图"),
      state: isConfirming ? "current" : (ticket ? "done" : "idle"),
    },
  ];

  const wrap = el("div", "pipeline-steps");
  for (const s of steps) {
    const row = el("div", `pipeline-step step-${s.state}`);
    const badgeNode = el("span", "pipeline-num", s.num);
    const body = el("div", "pipeline-body");
    body.append(el("strong", "", s.title), el("small", "", s.desc));
    row.append(badgeNode, body);
    wrap.append(row);
  }
  return wrap;
}

function renderPipelineTrace(state, ticket) {
  const liveBox = $("pipeline-live");
  if (liveBox) {
    const head = el("div", "pipeline-live-head");
    head.append(
      el("span", "pipeline-live-kicker", "🧠 LangGraph 5层实时链路"),
      button("展开大图", "pipeline-expand-btn", () => $("demo-dialog").showModal())
    );
    liveBox.replaceChildren(head, buildPipelineView(state, ticket));
  }
  const modalBox = $("pipeline-modal-diagram");
  if (modalBox) {
    modalBox.replaceChildren(buildPipelineView(state, ticket));
  }
}

function renderPanel() {
  const state = latest;
  if (!state) return;
  const focusTicket = state.focus && state.focus.ticket_id ? state.tickets.find((item) => item.ticket_id === state.focus.ticket_id) : null;
  const picked = viewTicket ? state.tickets.find((item) => item.ticket_id === viewTicket) : null;
  if (!picked) viewTicket = null;
  const ticket = picked || focusTicket || null;
  shownOrder = ticket ? ticket.order_id : state.focus ? state.focus.order_id : null;
  if (shownOrder) switchMjByOrder(shownOrder);
  renderPipelineTrace(state, ticket);
  renderTickets(state, ticket);
  renderOthers(state, ticket);
  renderJourney(state, ticket);
  markOrders();
  renderPicks(state);
  handoffWaiting = state.handoffs.some((item) => item.status === "waiting");
  $("handoff-label").textContent = handoffWaiting ? "人工排队中" : "转人工";
  $("handoff").classList.toggle("waiting", handoffWaiting);
  updateControls();
}

function renderOrders() {
  const query = $("order-search").value.trim().toLowerCase();
  const matching = orders.filter((order) => `${order.order_id} ${order.merchant} ${order.case || ""}`.toLowerCase().includes(query));
  const shown = query || expandedOrders ? matching : matching.slice(0, 3);
  $("orders").replaceChildren(...shown.map((order) => {
    const row = el("div", "order");
    row.dataset.orderId = order.order_id;
    row.addEventListener("click", (event) => {
      if (!event.target.closest("button")) switchMjByOrder(order.order_id);
    });
    const text = el("div", "order-text");
    const topLine = el("div", "order-top-line");
    topLine.append(el("strong", "", order.merchant), el("span", "order-price", `¥${order.amount_yuan}`));
    const metaRow = el("div", "order-meta-row");
    metaRow.append(el("span", "order-meta", `${order.order_id} · ${ORDER_STATUS[order.status] || order.status}`));
    if (order.case) metaRow.append(el("span", "order-case-pill", order.case.replace(/^P0\d\s*/, "")));
    const bottom = el("div", "order-bottom");
    const time = order.delivered_at ? `${order.expected_at} → ${order.delivered_at}` : `预计 ${order.expected_at}`;
    const actions = el("span", "order-actions");
    actions.append(button("详情", "small detail-button", () => { switchMjByOrder(order.order_id); showOrderDetail(order); }),
      button("咨询", "small", () => pickOrderAction(order)));
    bottom.append(el("span", "order-time", time), actions);
    text.append(topLine, metaRow, bottom);
    row.append(icon("bowl", "order-art"), text);
    return row;
  }));
  if (!matching.length) $("orders").append(el("p", "empty search-empty", "未找到订单"));
  if (orders.length === 1 && orders[0].order_id === "ORD101") {
    const switchBtn = button("切换到顾客 01（含 8 笔主测试单）", "show-more", async () => {
      try { await enter((await api("/api/customer/login", { customer_id: "U001" })).customer); }
      catch (error) { showStatus(error.message, true); }
    });
    switchBtn.append(icon("arrow-right"));
    $("orders").append(switchBtn);
  }
  $("more-orders").hidden = Boolean(query) || matching.length <= 3;
  $("more-orders").replaceChildren(el("span", "", expandedOrders ? "收起" : `全部订单 · ${matching.length}`), icon("chevron-down"));
  $("more-orders").setAttribute("aria-expanded", String(expandedOrders));
  markOrders();
  updateControls();
}

function notifyChanges(state) {
  const now = new Map([...state.tickets.map((item) => [item.ticket_id, item.status]), ...state.handoffs.map((item) => [item.handoff_id, item.status])]);
  if (seen) {
    for (const ticket of state.tickets) {
      const before = seen.get(ticket.ticket_id);
      if (!before || before === ticket.status) continue;
      if (ticket.status === "approved") toast(`${ticket.order_id} 审核通过，¥${ticket.coupon_issued_yuan} 补偿券已发放`);
      else if (ticket.status === "rejected") toast(`${ticket.order_id} 审核未通过，可查看商家说明`);
      else if (ticket.status === "needs_info") toast(`${ticket.order_id}：商家请你补充信息`);
    }
    for (const item of state.handoffs) if (seen.get(item.handoff_id) === "waiting" && item.status === "replied") toast("人工客服已回复");
  }
  seen = now;
}

function signOut() {
  informationDrafts.clear();
  signedIn = false;
  lastState = "";
  lastChat = "";
  latest = null;
  seen = null;
  lastFocus = null;
  viewTicket = null;
  othersOpen = null;
  // The next account must not see this account's notice.
  clearTimeout(toastTimer);
  $("toast").classList.remove("show");
  setSignedIn(null);
}

async function refresh() {
  let state;
  try { state = await api("/api/customer/state"); }
  catch (error) { if (error.status === 401) return signOut(); throw error; }
  const key = JSON.stringify(state);
  if (key === lastState) return;
  lastState = key;
  notifyChanges(state);
  // A new message or confirmation brings the panel back to the order being discussed.
  const focusKey = [state.focus && state.focus.order_id, state.messages.length, Boolean(state.confirmation)].join("|");
  if (focusKey !== lastFocus) { lastFocus = focusKey; viewTicket = null; }
  latest = state;
  renderMessages(state.messages, state.handoffs);
  renderConfirmation(state.confirmation);
  renderPanel();
}

async function act(work) {
  if (busy) return;
  busy = true;
  updateControls();
  showStatus("处理中…");
  try {
    // A step may return a short note for the status line; API responses are not notes.
    const note = await work();
    showStatus(typeof note === "string" ? note : "");
  }
  catch (error) { showStatus(error.message, true); }
  finally {
    busy = false;
    await refresh().catch((error) => showStatus(error.message, true));
    updateControls();
  }
}

function send(raw, fromInput) {
  const text = raw.trim();
  if ((!text && !draftMedia) || confirming) return;
  const media = draftMedia;
  if (fromInput) { $("input").value = ""; updateCount(); }
  setPlusTray(false);
  if (!media && text) {
    pendingUserText = text;
    if (latest) renderMessages(latest.messages, latest.handoffs);
  }
  act(async () => {
    let result;
    try {
      if (media) {
        const body = new FormData();
        if (text) body.append("text", text);
        body.append("attachment", media.file, media.file.name);
        result = await api("/api/customer/handoff", body);
        clearDraftMedia();
      } else {
        result = await api("/api/customer/messages", { text });
      }
    } finally {
      pendingUserText = "";
      lastState = "";
    }
    if (media) return "附件已交给人工客服，AI 不会自动识别附件内容。";
    return result.outcome === "handoff_waiting" ? "已在排队，人工客服会在对话里回复" : "";
  });
}

function updateCount() { $("input-count").textContent = `${$("input").value.length} / 500`; }

async function enter(customer) {
  informationDrafts.clear();
  orders = (await api("/api/customer/orders")).orders;
  expandedOrders = false;
  $("order-search").value = "";
  lastState = "";
  lastChat = "";
  seen = null;
  lastFocus = null;
  viewTicket = null;
  renderOrders();
  await refresh();
  signedIn = true;
  setSignedIn(customer.display_name);
}

async function boot() {
  const info = await api("/api/health");
  policy = info.policy;
  renderMeta(info);
  renderLogin(info.customers, "customer_id", async (customerId) => {
    try { await enter((await api("/api/customer/login", { customer_id: customerId })).customer); }
    catch (error) { showStatus(error.message, true); }
  });
  $("quick").replaceChildren(...QUICK.map(([label, text]) => button(label, "suggestion", () => { $("demo-dialog").close(); send(text); })));
  $("composer").addEventListener("submit", (event) => { event.preventDefault(); send($("input").value, true); });
  $("attach").addEventListener("click", () => { setPlusTray(false); $("attachment-input").click(); });
  $("attachment-input").addEventListener("change", () => {
    const file = $("attachment-input").files[0];
    if (file && setDraftMedia(file, "image")) $("attachment-input").value = "";
  });
  $("record").addEventListener("click", toggleRecording);
  if ($("tray-record")) $("tray-record").addEventListener("click", () => { setPlusTray(false); toggleRecording(); });
  if ($("plus-toggle")) $("plus-toggle").addEventListener("click", () => setPlusTray(!plusOpen));
  if ($("open-order-sheet")) $("open-order-sheet").addEventListener("click", openOrderSheet);
  if ($("tray-orders")) $("tray-orders").addEventListener("click", openOrderSheet);
  if ($("tray-pipeline")) $("tray-pipeline").addEventListener("click", () => { setPlusTray(false); $("demo-dialog").showModal(); });
  if ($("open-pipeline")) $("open-pipeline").addEventListener("click", () => $("demo-dialog").showModal());
  if ($("close-order-sheet")) $("close-order-sheet").addEventListener("click", () => $("order-sheet-dialog").close());
  if ($("order-sheet-dialog")) {
    $("order-sheet-dialog").addEventListener("click", (e) => {
      if (e.target === $("order-sheet-dialog")) $("order-sheet-dialog").close();
    });
  }
  $("input").addEventListener("input", updateCount);
  $("input").addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey && !event.isComposing) { event.preventDefault(); send($("input").value, true); }
  });
  $("order-search").addEventListener("input", renderOrders);
  $("more-orders").addEventListener("click", () => { expandedOrders = !expandedOrders; renderOrders(); });
  $("confirm-yes").addEventListener("click", () => act(() => api("/api/customer/confirm", { answer: "confirm" })));
  $("confirm-no").addEventListener("click", () => act(() => api("/api/customer/confirm", { answer: "cancel" })));
  $("handoff").addEventListener("click", () => act(() => api("/api/customer/handoff", {})));
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
