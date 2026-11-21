"use strict";

const QUICK = [
  ["P01 晚到50分钟（可赔）", "我的外卖 ORD001 迟到了，可以申请补偿吗？"],
  ["多单对比（ORD001 vs ORD002）", "帮我同时对比一下 ORD001 和 ORD002 这两单，哪一单能赔？"],
  ["边界 恰好30:00（拒赔+安抚）", "我的外卖 ORD003 迟到了，可以申请补偿吗？"],
  ["边界 29分59秒（拒赔+安抚）", "我的外卖 ORD004 迟到了，可以申请补偿吗？"],
  ["边界 30分01秒（绿灯可赔）", "我的外卖 ORD005 迟到了，可以申请补偿吗？"],
  ["配送中查进度（ORD006）", "帮我查一下 ORD006 送到哪了"],
  ["弱网缺签收记录（ORD007）", "ORD007 怎么没有送达时间，能赔吗？"],
  ["食安异物熔断（ORD001 餐损）", "我 ORD001 的餐食里有异物，需要处理"],
  ["手滑单号纠错（ordoo6）", "帮我查下 ordoo6 到哪了"],
  ["P03 查他人订单（ORD101）", "帮我查一下 ORD101"],
  ["未提供订单号", "我的外卖迟到了，可以申请补偿吗？"],
  ["转人工客服", "我想找人工客服"],
];
const ORDER_STATUS = { delivered: "已送达", delivering: "配送中" };
const HANDOFF_NOTE = { waiting: "已转人工专席排队中，专员回复会直接显示在这里", replied: "人工客服专员已接入回复", cancelled: "已取消转人工" };
let signedIn = false;
let busy = false;
let confirming = false;
let lastState = "";
let lastChat = "";
let renderedMsgCount = 0;
let orders = [];
let expandedOrders = false;
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
let urgeCooldownUntil = 0;
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

// Non-blocking workspace: only lock the composer submit & active confirmation buttons while awaiting response.
function updateControls() {
  const locked = busy || confirming;
  $("input").disabled = confirming;
  $("send").disabled = locked || Boolean(recorder);
  $("attach").disabled = locked || Boolean(recorder);
  $("attachment-input").disabled = locked || Boolean(recorder);
  $("record").disabled = locked;
  if ($("tray-record")) $("tray-record").disabled = locked;
  if ($("tray-photo")) $("tray-photo").disabled = locked || Boolean(recorder);
  for (const node of document.querySelectorAll("#confirm-yes, #confirm-no, .handoff-cancel")) node.disabled = busy;
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

function bubble(role, text, tag, isNew = false) {
  const row = el("div", `bubble-row ${role}${isNew ? " is-new" : ""}`);
  if (role === "assistant" || role === "human") {
    const head = el("div", "bubble-sender-head");
    if (role === "human") {
      const specialistIcon = icon("person", "bubble-specialist-icon");
      head.append(specialistIcon, el("span", "bubble-tag", tag || "人工客服"));
    } else {
      const avatar = mascotImg("bubble-avatar-img");
      head.append(avatar, el("span", "bubble-tag", tag || "AI"));
    }
    row.append(head);
  } else if (tag) {
    row.append(el("span", "bubble-tag", tag));
  }
  row.append(el("div", "bubble", text));
  return row;
}

// Meituan Waimai style Rich Order Card inside chat stream (customer-safe progress wording, zero rider-blaming).
function chatOrderCard(order) {
  const card = el("article", "waimai-chat-card");
  const shopRow = el("div", "waimai-shop-row");
  const shopAvatar = mascotImg("waimai-shop-avatar");
  shopRow.append(shopAvatar, el("span", "waimai-shop-name", `${order.merchant}（港城店）`));
  if (order.case) {
    shopRow.append(el("span", "order-case-pill", order.case.replace(/^P0\d\s*/, "")));
  }
  const title = el("h4", "waimai-card-title", order.status === "delivering" ? "订单配送中 · 实时进度" : "已核实订单履约信息");
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
    : (order.status === "delivering" ? `配送中（预计 ${order.expected_at} 送达）` : `预计 ${order.expected_at} · 签收同步中`);
  const rows = [
    ["订单编号：", order.order_id],
    ["配送时间：", timeVal],
    ["进度说明：", order.customer_progress_note || "系统已核实备餐与配送记录"],
  ];
  for (const [k, v] of rows) {
    meta.append(el("dt", "", k), el("dd", "", v));
  }

  const footBtn = button(
    order.status === "delivering" ? "查看实时配送详情" : "查看完整订单详情",
    "waimai-card-btn",
    () => showOrderDetail(order)
  );
  card.append(shopRow, title, gallery, meta, footBtn);
  return card;
}

// Dedicated P0 Food Safety Emergency Card rendered whenever food-safety / foreign-object issue is detected.
function foodSafetyEmergencyCard() {
  const card = el("div", "food-safety-card");
  const head = el("div", "food-safety-head");
  head.append(el("span", "food-safety-badge", "P0 食安绿色通道"), el("strong", "", "餐品异物 / 受损优先处理"));
  const desc = el("p", "", "请保留餐品原貌拍照上传凭证，系统将绕开普通超时队列直派食安应急专员优先核实处理。");
  const actions = el("div", "food-safety-actions");
  actions.append(
    button("📷 上传异物/餐损照片", "small primary", () => $("attachment-input").click()),
    button("⚡ 直连食安人工专席", "small secondary", () => act(() => api("/api/customer/handoff", { text: "【P0食安绿色通道】餐品异常需专员优先处理" })))
  );
  card.append(head, desc, actions);
  return card;
}

function attachmentBubble(item) {
  const row = el("div", "bubble-row customer attachment-row");
  row.append(el("span", "bubble-tag", "顾客凭证"), attachmentList(item.attachments, { customer: true }));
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
  if (item.status === "replied") {
    nodes.push(bubble("human", item.reply_text, "人工客服"));
    for (const f of item.followups || []) {
      nodes.push(bubble(f.sender_role === "customer" ? "customer" : "human", f.text, f.sender_role === "customer" ? "" : "人工客服"));
    }
    const replyBar = el("div", "customer-followup-bar");
    const fInput = el("input", "customer-followup-input");
    fInput.type = "text";
    fInput.maxLength = 500;
    fInput.placeholder = "向人工专员追加补充说明…";
    fInput.hidden = true;
    const sendFollow = button("发送留言", "small primary", () => {
      const msg = fInput.value.trim();
      if (!msg) { fInput.focus(); return; }
      act(async () => {
        await api(`/api/customer/handoffs/${encodeURIComponent(item.handoff_id)}/followup`, { text: msg });
        fInput.value = "";
      });
    });
    sendFollow.hidden = true;
    const replyBtn = button("向人工专员追加留言", "small secondary", () => {
      replyBtn.hidden = true;
      fInput.hidden = false;
      sendFollow.hidden = false;
      fInput.focus();
    });
    replyBar.append(replyBtn, fInput, sendFollow);
    nodes.push(replyBar);
  }
  return nodes;
}

function welcome() {
  const box = el("div", "chat-welcome");
  const hero = el("div", "welcome-hero");
  const copy = el("div", "welcome-copy");
  const badgeRow = el("div", "welcome-badge-row");
  badgeRow.append(
    el("span", "welcome-kicker", "AI 智能客服"),
    el("span", "welcome-kicker specialist-kicker", "值班人工专席")
  );
  copy.append(
    badgeRow,
    el("h3", "", "你好！我是 AI 订单客服，想咨询哪笔订单？"),
    el("p", "welcome-note", "我是生成式 AI 客服（不是真人坐席）。您可以从左侧「我的订单」选择咨询，支持多单同时对比；涉及餐损异物可点下方图片按钮上传照片直连人工专席。")
  );
  hero.append(careBuddy("buddy-welcome"), copy);

  const suggestions = el("div", "suggestion-row");
  suggestions.append(el("span", "suggestion-title", "常见场景一键体验"));
  for (const [label, text] of [
    ["ORD001 晚到了 50 分钟", "我的外卖 ORD001 迟到了，可以申请补偿吗？"],
    ["同时对比 ORD001 和 ORD002", "帮我同时对比一下 ORD001 和 ORD002 这两单，哪一单能赔？"],
    ["ORD001 餐品异物绿色通道", "我 ORD001 的餐食里有异物，需要申请理赔"],
    ["未带单号咨询", "我的外卖迟到了，可以申请补偿吗？"],
  ]) {
    const suggestion = button(label, "suggestion", () => send(text));
    suggestion.append(icon("arrow-up-right"));
    suggestions.append(suggestion);
  }
  box.append(hero, suggestions);
  return box;
}

function typingBubble() {
  const row = el("div", "bubble-row assistant typing-row");
  const head = el("div", "bubble-sender-head");
  const avatar = mascotImg("bubble-avatar-img");
  head.append(avatar, el("span", "bubble-tag", "AI"));
  const bub = el("div", "bubble typing-bubble");
  bub.append(el("span", "typing-text", "正在核实订单记录"), el("span", "typing-dots", "···"));
  row.append(head, bub);
  return row;
}

// Flicker-free incremental awareness: only animate newly arrived messages & preserve user scroll if reading upward.
function renderMessages(messages, handoffs) {
  const key = JSON.stringify([messages, handoffs, pendingUserText, orders.length]);
  if (key === lastChat) return;
  lastChat = key;
  const box = $("messages");
  const wasNearBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 120;

  if (!messages.length && !handoffs.length && !pendingUserText) {
    renderedMsgCount = 0;
    box.replaceChildren(welcome());
    updateControls();
    return;
  }
  const nodes = [];
  const place = (index) => {
    for (const item of handoffs) if (Math.min(item.after, messages.length) === index) nodes.push(...handoffBlock(item));
  };
  messages.forEach((item, index) => {
    place(index);
    const isNew = index >= renderedMsgCount;
    if (item.role === "tool") {
      const oid = item.text.replace("查单工具 query_order：", "").trim();
      const line = el("p", "tool-line");
      line.append(icon("search"), el("span", "", `已核实订单：${oid}`));
      nodes.push(line);
      const matchedOrder = orders.find((o) => o.order_id === oid);
      if (matchedOrder) nodes.push(chatOrderCard(matchedOrder));
    } else {
      nodes.push(bubble(item.role, item.text, item.role === "assistant" ? "AI" : "", isNew));
      if (item.role === "assistant" && /食安|异物|停止食用|绿色通道/.test(item.text)) {
        nodes.push(foodSafetyEmergencyCard());
      }
    }
  });
  place(messages.length);
  renderedMsgCount = messages.length;
  if (pendingUserText) {
    nodes.push(bubble("customer", pendingUserText, "", true));
    nodes.push(typingBubble());
  }
  box.replaceChildren(...nodes);
  if (wasNearBottom || pendingUserText) {
    box.scrollTop = box.scrollHeight;
  }
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
    el("span", "", eligible ? "已达标 · ¥10" : "30m 准时保容差区")
  );
  const track = el("div", "sla-track");
  const fill = el("div", "sla-fill");
  fill.style.width = `${Math.max(6, pct)}%`;
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
  input.placeholder = "填写需要补充的情况说明（切勿输入敏感隐私）";
  input.value = informationDrafts.get(ticket.ticket_id) || "";
  input.addEventListener("input", () => informationDrafts.set(ticket.ticket_id, input.value));
  const btnRow = el("div", "actions");
  const submit = el("button", "primary", "提交补充");
  submit.type = "submit";
  submit.dataset.action = "submit-information";
  const uploadPic = button("附带图片凭证", "secondary", () => $("attachment-input").click());
  btnRow.append(submit, uploadPic);
  form.append(label, input, btnRow);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const text = input.value.trim();
    if (busy || confirming) return;
    if (!text) { input.focus(); showStatus("请填写补充说明", true); return; }
    act(async () => {
      let finalNote = text;
      if (draftMedia) {
        const body = new FormData();
        body.append("text", `【工单 ${ticket.ticket_id} · ${ticket.order_id} 补充凭证】${text}`);
        body.append("attachment", draftMedia.file, draftMedia.file.name);
        await api("/api/customer/handoff", body);
        clearDraftMedia();
        finalNote = `${text}（已附带上传图片/语音凭证）`;
      }
      await api(`/api/customer/tickets/${encodeURIComponent(ticket.ticket_id)}/information`, { text: finalNote });
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
  if (ticket.status === "pending") text.append(el("p", "", "等待审核处理，预计 24 小时内处理"));
  else if (ticket.status === "rejected") text.append(el("p", "", "本次未发放，详见下方说明"));
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
    note.append(el("span", "", "处理说明"), el("p", "", ticket.review_note));
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

// Rider-respectful live delivery radar (no premature phone harassment when not late, + 15-min cooldown).
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
  let kind, title, note, amount = null, action = null;
  if (!focus.verified) {
    kind = "unverified"; title = "无法核实这笔订单"; note = "当前账号下没有这笔订单。请核对订单号，或从「我的订单」中选择。";
  } else if (claim) {
    kind = "confirm"; title = "待你确认"; amount = claim.proposed_coupon_yuan; note = "核对对话框里的信息后点「确认提交」";
  } else if (focus.status === "pending") {
    kind = "eligible"; title = "符合申请条件"; amount = focus.proposed_coupon_yuan; note = "提交后进入审核流程";
    action = button("申请补偿", "primary", () => send(`我的外卖 ${focus.order_id} 迟到了，可以申请补偿吗？`));
  } else if (focus.reason_code === "delay_below_threshold") {
    const late = focus.late_seconds > 0 ? `晚到 ${delayText(focus.late_seconds)}` : "没有晚到";
    const granted = ((latest && latest.goodwill_grants) || []).find((g) => g.order_id === focus.order_id);
    if (granted) {
      kind = "eligible";
      title = "已到账 · 准时保暖心关怀券";
      amount = granted.amount_yuan;
      note = `本单${late}（临界延迟体验保护），平台体验金池已为您秒发 ¥${granted.amount_yuan} 无门槛暖心券（商家 ¥0 承担）。`;
    } else {
      kind = "ineligible"; title = "未达到申请条件";
      note = `本单${late}；需${ruleText()}才能申请。`;
      if (focus.late_seconds >= 900) {
        action = button("一键秒领 ¥3 准时保暖心券", "primary", () => act(async () => {
          const res = await api("/api/customer/goodwill", { order_id: focus.order_id });
          toast(`${focus.order_id} 已秒领 ¥${res.grant.amount_yuan} 准时保暖心关怀券`);
          return `已为您发放 ¥${res.grant.amount_yuan} 平台准时保暖心关怀券`;
        }));
      }
    }
  } else if (focus.reason_code === "not_delivered") {
    kind = "delivering"; title = "订单正在正常配送"; note = `送达后如${ruleText()}，可随时申请准时保补偿。`;
  } else {
    kind = "unknown"; title = "签收时间同步核验中"; note = "因楼宇弱网暂未同步签收时间，可上传截图或点「转人工」核实。";
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
      ["预计送达", order.expected_at], ["实际送达", order.delivered_at || "配送中"],
      ["晚到", focus.late_seconds === null || focus.late_seconds === undefined ? "—" : delayText(focus.late_seconds)],
    ]));
    const attr = attributionBox(order);
    if (attr) card.append(attr);
    if (focus.reason_code === "not_delivered") {
      const radar = el("div", "rider-radar");
      const headRow = el("div", "radar-head");
      headRow.append(el("span", "radar-pulse"), el("strong", "", `实时配送守护 · 距您约 ${order.rider_distance_m || 380}m`));
      const sub = el("p", "", `预计 ${order.rider_eta_min || 3} 分钟内准时送达。骑手过路口期间已开启免打扰安全保护，若超时系统将自动提醒您申领准时保。`);
      const watchBtn = button("开启送达静默提醒", "secondary urge-button", () => {
        if (Date.now() < urgeCooldownUntil) {
          toast("已为您开启准时保静默守护，请耐心等待骑手安全送达");
          return;
        }
        urgeCooldownUntil = Date.now() + 15 * 60 * 1000;
        toast(`${order.order_id} 已开启静默送达提醒（不打扰骑手驾驶安全）`);
      });
      radar.append(headRow, sub, watchBtn);
      card.append(radar);
    }
  }
  if (action) { action.append(icon("arrow-right")); card.append(action); }
  return card;
}

function focusHint() {
  const box = el("div", "focus-hint");
  box.append(icon("search"), el("p", "", "在对话里发订单号，或点左侧「我的订单」里的「咨询」，这里会实时同步处理进度。"));
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
    ["下单时间", order.ordered_at || "17:20"], ["备餐完成", order.prep_done_at ? `${order.prep_done_at}（预计备餐 ${order.prep_promised_at || "17:35"}）` : "—"],
    ["交接配送", order.picked_up_at || "—"], ["预计送达", order.expected_at],
    ["实际送达", order.delivered_at || (order.status === "delivering" ? "配送中" : "同步核验中")],
  ];
  root.append(heading, hero);
  if (chain) root.append(chain);
  if (attr) root.append(attr);
  root.append(
    el("h3", "order-detail-section", "餐品明细"), itemList,
    el("h3", "order-detail-section", "配送信息"), facts(rows),
    el("p", "order-detail-note", "课堂教学演示订单 · 账单与配送时间仅供测试。")
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
  const label = draftMedia.kind === "image" ? "图片凭证待发送" : "语音留言待发送";
  const row = el("div", "draft-media-row");
  row.append(icon(draftMedia.kind === "image" ? "image" : "audio"), el("strong", "", label),
    el("small", "", `${draftMedia.file.name} · ${(draftMedia.file.size / 1024 / 1024).toFixed(2)} MB`));
  const remove = button("移除", "media-remove", clearDraftMedia);
  remove.prepend(icon("trash"));
  const quickSend = button("立即提交专席", "small primary draft-send-btn", () => send($("input").value, true));
  const btnWrap = el("div", "draft-media-actions");
  btnWrap.append(remove, quickSend);
  row.append(btnWrap);
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
  showStatus(kind === "image" ? "图片凭证已就绪，点发送即可直连人工专席核验。" : "语音留言已就绪，点发送即可提交人工专席。", false);
  return true;
}

function formatRecordingTime() {
  const seconds = Math.floor((Date.now() - recorderStartedAt) / 1000);
  return `录音中 ${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}

function showRecordButton(recording) {
  const node = $("record");
  node.classList.toggle("recording", recording);
  node.replaceChildren(icon(recording ? "stop" : "mic"));
  const label = el("span", recording ? "record-time-pill" : "sr-only", recording ? formatRecordingTime() : "语音");
  label.id = "record-label";
  node.append(label);
  node.setAttribute("aria-label", recording ? "停止语音录制" : "录制语音留言");
}

function stopRecorderTracks() {
  clearInterval(recorderTimer);
  recorderTimer = 0;
  for (const track of recorderStream?.getTracks() || []) track.stop();
  recorderStream = null;
  recorder = null;
  showRecordButton(false);
  updateControls();
}

async function toggleRecording() {
  if (recorder) { recorder.stop(); return; }
  if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
    showStatus("当前浏览器不支持录音，请直接输入文字或上传图片凭证。", true);
    return;
  }
  const preferred = ["audio/webm", "audio/ogg", "audio/mp4"].find((type) => MediaRecorder.isTypeSupported?.(type)) || "";
  try {
    recorderStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    recorderChunks = [];
    recorder = preferred ? new MediaRecorder(recorderStream, { mimeType: preferred }) : new MediaRecorder(recorderStream);
    recorder.addEventListener("dataavailable", (event) => { if (event.data.size) recorderChunks.push(event.data); });
    recorder.addEventListener("stop", () => {
      const type = (recorder.mimeType || preferred || "audio/webm").split(";", 1)[0];
      const ext = type.includes("ogg") ? "ogg" : type.includes("mp4") ? "m4a" : "webm";
      const file = new File(recorderChunks, `voice-${Date.now()}.${ext}`, { type });
      stopRecorderTracks();
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
    showStatus("未获得麦克风权限，您可以直接输入文字或点击相册上传图片凭证。", true);
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
    const glyph = btn.querySelector(".plus-glyph");
    if (glyph) glyph.textContent = plusOpen ? "×" : "+";
  }
}

function pickOrderAction(order, intent = "default") {
  switchMjByOrder(order.order_id);
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
  if (intent === "issue") {
    send(`我 ${order.order_id} 的餐品出现洒漏或异物问题，需要处理`);
    return;
  }
  if (intent === "lookup" || order.status === "delivering") {
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
    shop.append(icon("bowl", "sheet-shop-icon"), el("strong", "", `${order.merchant}`), el("span", "sheet-order-id", order.order_id));
    const statusText = order.case ? order.case.replace(/^P0\d\s*/, "") : (ORDER_STATUS[order.status] || order.status);
    top.append(shop, el("span", "order-case-pill", statusText));

    const rawItems = Array.isArray(order.items) && order.items.length ? order.items : ["招牌套餐 ×1"];
    const gallery = el("div", "waimai-food-gallery");
    const thumbs = el("div", "waimai-food-thumbs");
    let totalCount = 0;
    for (const raw of rawItems) {
      const [dishName, qtyRaw] = String(raw).split(" ×");
      totalCount += Number(qtyRaw) || 1;
      const foodItem = el("div", "waimai-food-item");
      foodItem.append(el("div", "waimai-food-pic", foodEmoji(dishName)), el("span", "waimai-food-name", dishName));
      thumbs.append(foodItem);
    }
    const priceCol = el("div", "waimai-price-col");
    priceCol.append(el("strong", "", `¥${Number(order.amount_yuan).toFixed(1)}`), el("small", "", `共 ${totalCount} 件`));
    gallery.append(thumbs, priceCol);

    const timeRow = el("div", "sheet-order-foot");
    const timeStr = order.delivered_at ? `预计 ${order.expected_at} → 实际 ${order.delivered_at}` : `预计 ${order.expected_at}`;
    const actBtns = el("div", "sheet-order-actions");
    actBtns.append(button("详情", "small secondary", () => { $("order-sheet-dialog").close(); showOrderDetail(order); }));
    if (order.status === "delivering") {
      actBtns.append(button("查配送进度", "small primary", () => pickOrderAction(order, "lookup")));
    } else {
      actBtns.append(
        button("餐损/异物", "small secondary", () => pickOrderAction(order, "issue")),
        button("超时补偿", "small primary", () => pickOrderAction(order, "default"))
      );
    }
    timeRow.append(el("span", "sheet-order-time", timeStr), actBtns);
    card.append(top, gallery, timeRow);
    list.append(card);
  }
}

function openOrderSheet() {
  setPlusTray(false);
  renderOrderSheet();
  const dialog = $("order-sheet-dialog");
  if (dialog && !dialog.open) dialog.showModal();
}

function renderTicketSheet() {
  const list = $("ticket-sheet-list");
  if (!list) return;
  const state = latest;
  list.replaceChildren();
  const tickets = (state && state.tickets) || [];
  const handoffs = ((state && state.handoffs) || []).filter((h) => h.status !== "cancelled");

  if (!tickets.length && !handoffs.length) {
    const empty = el("div", "sheet-empty");
    empty.append(
      mascotImg("sheet-empty-avatar"),
      el("strong", "", "当前暂无售后申请或人工工单"),
      el("p", "", "已送达订单若晚到超过 30 分钟可提交补偿申请，审核进度与满意度评价将同步展示在此处。"),
      button("选择需要咨询的订单", "welcome-order-cta", () => {
        $("ticket-sheet-dialog").close();
        openOrderSheet();
      })
    );
    list.append(empty);
    return;
  }

  for (const ticket of tickets) {
    const card = el("article", "sheet-order-card");
    const top = el("div", "sheet-order-top");
    const titleWrap = el("div", "sheet-order-shop");
    titleWrap.append(icon("ticket", "sheet-shop-icon"), el("strong", "", `售后单 ${ticket.ticket_id} · ${ticket.order_id}`), badge(ticket.status));
    top.append(titleWrap, el("span", "order-price", ticket.coupon_issued_yuan ? `已发 ¥${ticket.coupon_issued_yuan}` : `申请 ¥${ticket.proposed_coupon_yuan}`));
    const meta = el("dl", "waimai-meta-grid");
    const rows = [
      ["配送超时：", delayText(ticket.late_seconds)],
      ["当前状态：", STATUS_TEXT[ticket.status] || ticket.status],
    ];
    if (ticket.review_note) rows.push(["处理说明：", ticket.review_note]);
    for (const [k, v] of rows) meta.append(el("dt", "", k), el("dd", "", v));
    const foot = el("div", "sheet-order-foot");
    const actBtns = el("div", "sheet-order-actions");
    actBtns.append(
      button("查看详情卡片", "small primary", () => {
        viewTicket = ticket.ticket_id;
        $("ticket-sheet-dialog").close();
        renderPanel();
        $("tickets-panel").scrollIntoView({ behavior: "smooth", block: "start" });
      })
    );
    foot.append(el("span", "sheet-order-time", `更新于 ${clock(ticket.decided_at || ticket.created_at)}`), actBtns);
    card.append(top, meta, foot);
    list.append(card);
  }
}

function openTicketSheet() {
  setPlusTray(false);
  renderTicketSheet();
  const dialog = $("ticket-sheet-dialog");
  if (dialog && !dialog.open) dialog.showModal();
}

// Contextual order-picker bar: appears ONLY when the customer asked a question without a verified order (zero permanent clutter!).
function renderPicks(state) {
  const box = $("order-picks");
  const hasMessages = state.messages && state.messages.length > 0;
  const needsOrderChoice = hasMessages && !state.confirmation && (!state.focus || !state.focus.verified) && orders.length > 0;
  box.hidden = !needsOrderChoice;
  if (!needsOrderChoice) { box.replaceChildren(); return; }

  const bar = el("div", "waimai-floating-pills");
  bar.append(el("span", "picks-prompt", "点选订单核实："));
  for (const order of orders.slice(0, 3)) {
    const pickBtn = button(
      `${order.order_id} · ¥${order.amount_yuan}`,
      "pick waimai-pill waimai-pill-primary",
      () => pickOrderAction(order)
    );
    pickBtn.dataset.pickOrder = order.order_id;
    bar.append(pickBtn);
  }
  if (orders.length > 3) {
    bar.append(button(`全部订单 (${orders.length})`, "waimai-pill", () => openOrderSheet()));
  }
  box.replaceChildren(bar);
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
  const badgeNode = $("tray-ticket-badge");
  if (badgeNode) {
    const activeCount = (state.tickets ? state.tickets.length : 0) + (state.handoffs ? state.handoffs.filter((h) => h.status !== "cancelled").length : 0);
    badgeNode.hidden = activeCount === 0;
    badgeNode.textContent = String(activeCount);
  }
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
    actions.append(button("详情", "small detail-button", () => { switchMjByOrder(order.order_id); showOrderDetail(order); }));
    if (order.status === "delivered") {
      actions.append(button("餐损", "small secondary", () => pickOrderAction(order, "issue")));
    }
    actions.append(button("咨询", "small", () => pickOrderAction(order)));
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
  const handoffDigest = state.handoffs.map((h) => [h.handoff_id, `${h.status}:${(h.followups || []).length}`]);
  const now = new Map([...state.tickets.map((item) => [item.ticket_id, item.status]), ...handoffDigest]);
  if (seen) {
    for (const ticket of state.tickets) {
      const before = seen.get(ticket.ticket_id);
      if (!before || before === ticket.status) continue;
      if (ticket.status === "approved") toast(`${ticket.order_id} 审核通过，¥${ticket.coupon_issued_yuan} 补偿券已发放`);
      else if (ticket.status === "rejected") toast(`${ticket.order_id} 审核未通过，可查看处理说明`);
      else if (ticket.status === "needs_info") toast(`${ticket.order_id}：专员请您补充说明`);
    }
    for (const item of state.handoffs) {
      const prev = seen.get(item.handoff_id);
      const curr = `${item.status}:${(item.followups || []).length}`;
      if (prev && prev !== curr && item.status === "replied") toast("人工客服已回复");
    }
  }
  seen = now;
}

function signOut() {
  informationDrafts.clear();
  signedIn = false;
  lastState = "";
  lastChat = "";
  renderedMsgCount = 0;
  latest = null;
  seen = null;
  lastFocus = null;
  viewTicket = null;
  othersOpen = null;
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
  showStatus("正在核实…");
  try {
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
    if (media) return "凭证已加密提交至人工客服专席，回复将显示在上方对话流中。";
    return result.outcome === "handoff_waiting" ? "已在人工专席排队中，回复将显示在对话流内" : "";
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
  renderedMsgCount = 0;
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
  if ($("tray-photo")) $("tray-photo").addEventListener("click", () => { setPlusTray(false); $("attachment-input").click(); });
  $("attachment-input").addEventListener("change", () => {
    const file = $("attachment-input").files[0];
    if (file && setDraftMedia(file, "image")) $("attachment-input").value = "";
  });
  $("record").addEventListener("click", toggleRecording);
  if ($("tray-record")) $("tray-record").addEventListener("click", () => { setPlusTray(false); toggleRecording(); });
  if ($("plus-toggle")) $("plus-toggle").addEventListener("click", () => setPlusTray(!plusOpen));
  if ($("tray-orders")) $("tray-orders").addEventListener("click", openOrderSheet);
  if ($("tray-tickets")) $("tray-tickets").addEventListener("click", openTicketSheet);
  if ($("close-order-sheet")) $("close-order-sheet").addEventListener("click", () => $("order-sheet-dialog").close());
  if ($("close-ticket-sheet")) $("close-ticket-sheet").addEventListener("click", () => $("ticket-sheet-dialog").close());
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
