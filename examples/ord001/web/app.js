"use strict";

// Shared UI and API helpers. Server content always enters the page through textContent.
const STATUS_TEXT = { pending: "审核中", needs_info: "待补充", approved: "已通过", rejected: "未通过" };
const $ = (id) => document.getElementById(id);
const ICONS = {
  bowl: ["M3 11h18c-.7 6-4 9-9 9s-8.3-3-9-9Z", "M2 11h20M8 4c-2 2 2 3 0 5M13 3c-2 2 2 3 0 5M18 4c-2 2 2 3 0 5"],
  chat: ["M21 11.5a8.5 8.5 0 0 1-8.5 8.5H4l-2 2V11.5A8.5 8.5 0 0 1 10.5 3h2a8.5 8.5 0 0 1 8.5 8.5Z", "M7 10h10M7 14h6"],
  inbox: ["M4 3h16l2 11v7H2v-7L4 3Z", "M2 14h6l2 3h4l2-3h6M8 7h8M8 10h5"],
  info: ["M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20Z", "M12 11v6M12 7h.01"],
  shield: ["M12 2 3 6v6c0 5 9 10 9 10s9-5 9-10V6l-9-4Z", "m8 12 3 3 5-6"],
  "arrow-up-right": ["M6 18 18 6M6 6h12v12"],
  "arrow-right": ["M4 12h16m-6-6 6 6-6 6"],
  "arrow-up": ["M12 20V4m-6 6 6-6 6 6"],
  "chevron-down": ["m6 9 6 6 6-6"],
  logout: ["M9 4H4v16h5M9 12h13m-5-5 5 5-5 5"],
  moon: ["M20.7 13A9 9 0 0 1 11 3.3 9 9 0 1 0 20.7 13Z"],
  sun: ["M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0ZM12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"],
  check: ["m5 12 4 4L19 6"],
  clock: ["M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0Z", "M12 6v6l4 2"],
  "file-check": ["M14 2H5v20h14V7l-5-5ZM14 2v5h5", "m8 14 3 3 5-6"],
  ticket: ["M3 5h18v5a2 2 0 0 0 0 4v5H3v-5a2 2 0 0 0 0-4V5Z", "M15 5v3m0 3v2m0 3v3"],
  search: ["M17 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0Z", "m15 15 6 6"],
  heart: ["M20.5 4.5A5.5 5.5 0 0 0 12 6a5.5 5.5 0 0 0-8.5-1.5C-2 10 12 21 12 21S26 10 20.5 4.5Z"],
  sparkles: ["m12 2 2.5 7.5L22 12l-7.5 2.5L12 22l-2.5-7.5L2 12l7.5-2.5L12 2Z"],
  close: ["m6 6 12 12M6 18 18 6"],
  refresh: ["M20 8a9 9 0 0 0-15-3L2 8m0-6v6h6M4 16a9 9 0 0 0 15 3l3-3m0 6v-6h-6"],
  reset: ["M3 11a9 9 0 1 1 2 7M3 4v7h7", "M12 7v5l3 2"],
  person: ["M16.5 7.5a4.5 4.5 0 1 1-9 0 4.5 4.5 0 0 1 9 0Z", "M3.5 21a8.5 8.5 0 0 1 17 0"],
  paperclip: ["m20.5 11.5-8.8 8.8a5 5 0 0 1-7.1-7.1l9-9a3.3 3.3 0 0 1 4.7 4.7l-9.1 9.1a1.7 1.7 0 0 1-2.4-2.4l8.4-8.4"],
  mic: ["M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z", "M19 10v2a7 7 0 0 1-14 0v-2M12 19v3m-4 0h8"],
  stop: ["M6 6h12v12H6z"],
  image: ["M4 5h16v14H4z", "m4 16 4-4 3 3 3-4 6 6M8 9h.01"],
  audio: ["M5 10v4m3-7v10m4-13v16m4-13v10m3-7v4"],
  trash: ["M4 7h16M10 11v6m4-6v6M9 7V4h6v3m-9 0 1 13h10l1-13"],
  star: ["m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2L12 17.3l-5.6 2.9 1.1-6.2L3 9.6l6.2-.9L12 3Z"],
  bell: ["M18 9a6 6 0 1 0-12 0c0 7-3 8-3 8h18s-3-1-3-8Z", "M10.3 21a1.9 1.9 0 0 0 3.4 0"],
};

function svgEl(tag, attrs = {}) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, String(v));
  return node;
}

// Chibi Spider-Man delivery-service mascot (Q版蜘蛛侠外卖客服: red webbed mask, big white lenses, yellow rider helmet & headset).
function spideySvg(compact = false) {
  const svg = svgEl("svg", { viewBox: compact ? "0 0 100 100" : "0 0 120 128", class: "spidey-svg", "aria-hidden": "true" });
  if (compact) {
    svg.append(
      // Yellow rider helmet dome & playful wing tips
      svgEl("path", { d: "M16 42 L8 28 L25 33 Z", fill: "#FFB800", stroke: "#18191F", "stroke-width": "2.6", "stroke-linejoin": "round" }),
      svgEl("path", { d: "M84 42 L92 28 L75 33 Z", fill: "#FFB800", stroke: "#18191F", "stroke-width": "2.6", "stroke-linejoin": "round" }),
      svgEl("path", { d: "M20 44 C20 17 80 17 80 44 Z", fill: "#FFD000", stroke: "#18191F", "stroke-width": "2.8" }),
      // Chibi Spider-Man round head
      svgEl("path", { d: "M17 54 C17 28 83 28 83 54 C83 78 69 88 50 88 C31 88 17 78 17 54 Z", fill: "#E63946", stroke: "#18191F", "stroke-width": "2.8" }),
      // Mask web lines
      svgEl("path", { d: "M50 30 L50 87 M50 58 L21 40 M50 58 L79 40 M50 58 L20 68 M50 58 L80 68 M30 44 Q50 51 70 44 M26 67 Q50 75 74 67", stroke: "#9E1926", "stroke-width": "1.5", fill: "none", opacity: "0.65" }),
      // Helmet brim & mini spider badge
      svgEl("path", { d: "M15 41 Q50 31 85 41", stroke: "#18191F", "stroke-width": "3.2", fill: "none", "stroke-linecap": "round" }),
      svgEl("circle", { cx: "50", cy: "28", r: "6.5", fill: "#FFF8D6", stroke: "#18191F", "stroke-width": "2" }),
      svgEl("circle", { cx: "50", cy: "28", r: "2.6", fill: "#E63946" }),
      // Big expressive white Spider-Man lenses
      svgEl("path", { d: "M23 51 C25 40 39 41 46 52 C47 62 36 69 26 64 C21 61 21 55 23 51 Z", fill: "#FFFFFF", stroke: "#18191F", "stroke-width": "3.2", class: "spidey-lens" }),
      svgEl("path", { d: "M77 51 C75 40 61 41 54 52 C53 62 64 69 74 64 C79 61 79 55 77 51 Z", fill: "#FFFFFF", stroke: "#18191F", "stroke-width": "3.2", class: "spidey-lens" }),
      svgEl("circle", { cx: "31", cy: "52", r: "2.6", fill: "#BAE6FD", class: "spidey-lens" }),
      svgEl("circle", { cx: "69", cy: "52", r: "2.6", fill: "#BAE6FD", class: "spidey-lens" }),
      // Headset mic
      svgEl("rect", { x: "11", y: "51", width: "6", height: "13", rx: "3", fill: "#FFD000", stroke: "#18191F", "stroke-width": "2.2" }),
      svgEl("path", { d: "M14 63 Q22 79 40 78", stroke: "#18191F", "stroke-width": "2.4", fill: "none", "stroke-linecap": "round" }),
      svgEl("circle", { cx: "42", cy: "78", r: "3.2", fill: "#FFD000", stroke: "#18191F", "stroke-width": "1.8" })
    );
    return svg;
  }
  svg.append(
    // Soft golden glow behind mascot
    svgEl("circle", { cx: "60", cy: "66", r: "48", fill: "#FFF3B0", opacity: "0.55" }),
    // Chibi body (Spider-Red & Blue suit + yellow delivery strap)
    svgEl("path", { d: "M33 90 C33 77 87 77 87 90 L91 116 C91 120 29 120 29 116 Z", fill: "#E63946", stroke: "#18191F", "stroke-width": "2.8" }),
    svgEl("path", { d: "M33 93 L29 116 L43 116 L43 91 Z M87 93 L91 116 L77 116 L77 91 Z", fill: "#1D4ED8", stroke: "#18191F", "stroke-width": "2.2" }),
    svgEl("path", { d: "M42 86 L76 116", stroke: "#FFD000", "stroke-width": "6", "stroke-linecap": "round" }),
    // Waving chibi hand
    svgEl("path", { d: "M87 93 Q102 86 103 75", stroke: "#E63946", "stroke-width": "10", "stroke-linecap": "round" }),
    svgEl("path", { d: "M87 93 Q102 86 103 75", stroke: "#18191F", "stroke-width": "2.8", fill: "none", "stroke-linecap": "round" }),
    svgEl("circle", { cx: "103", cy: "73", r: "6.5", fill: "#E63946", stroke: "#18191F", "stroke-width": "2.6" }),
    // Chest mini spider emblem
    svgEl("circle", { cx: "60", cy: "102", r: "3.2", fill: "#18191F" }),
    svgEl("circle", { cx: "60", cy: "107", r: "4.2", fill: "#18191F" }),
    svgEl("path", { d: "M56 101 L50 98 M56 104 L49 104 M56 107 L50 111 M64 101 L70 98 M64 104 L71 104 M64 107 L70 111", stroke: "#18191F", "stroke-width": "1.8", "stroke-linecap": "round" }),
    // Helmet playful wing-ears (Meituan rider vibe + Spider web-wings)
    svgEl("path", { d: "M22 44 L9 27 L32 34 Z", fill: "#FFB800", stroke: "#18191F", "stroke-width": "2.8", "stroke-linejoin": "round" }),
    svgEl("path", { d: "M98 44 L111 27 L88 34 Z", fill: "#FFB800", stroke: "#18191F", "stroke-width": "2.8", "stroke-linejoin": "round" }),
    // Meituan-yellow delivery rider helmet
    svgEl("path", { d: "M24 46 C24 16 96 16 96 46 Z", fill: "#FFD000", stroke: "#18191F", "stroke-width": "2.8" }),
    // Big round Chibi Spider-Man head
    svgEl("path", { d: "M20 58 C20 30 100 30 100 58 C100 84 83 94 60 94 C37 94 20 84 20 58 Z", fill: "#E63946", stroke: "#18191F", "stroke-width": "2.8" }),
    // Spider-mask web lines
    svgEl("path", { d: "M60 33 L60 93 M60 61 L25 42 M60 61 L95 42 M60 61 L23 71 M60 61 L97 71 M60 61 L39 90 M60 61 L81 90 M36 47 Q60 55 84 47 M30 70 Q60 79 90 70 M41 84 Q60 90 79 84", stroke: "#9E1926", "stroke-width": "1.55", fill: "none", opacity: "0.62" }),
    // Helmet visor & badge
    svgEl("path", { d: "M17 44 Q60 32 103 44", stroke: "#18191F", "stroke-width": "3.6", fill: "none", "stroke-linecap": "round" }),
    svgEl("rect", { x: "45", y: "21", width: "30", height: "13", rx: "6.5", fill: "#FFFDF5", stroke: "#18191F", "stroke-width": "2.2" }),
    svgEl("circle", { cx: "60", cy: "27.5", r: "3.3", fill: "#E63946" }),
    svgEl("path", { d: "M55 25 L52 23 M55 28 L51 28 M65 25 L68 23 M65 28 L69 28", stroke: "#18191F", "stroke-width": "1.5", "stroke-linecap": "round" }),
    // Big expressive Chibi Spider-Man eye lenses
    svgEl("path", { d: "M27 54 C29 41 46 42 55 55 C56 66 43 74 31 68 C25 65 25 58 27 54 Z", fill: "#FFFFFF", stroke: "#18191F", "stroke-width": "3.5", class: "spidey-lens" }),
    svgEl("path", { d: "M93 54 C91 41 74 42 65 55 C64 66 77 74 89 68 C95 65 95 58 93 54 Z", fill: "#FFFFFF", stroke: "#18191F", "stroke-width": "3.5", class: "spidey-lens" }),
    svgEl("circle", { cx: "36", cy: "55", r: "3.2", fill: "#BAE6FD", class: "spidey-lens" }),
    svgEl("circle", { cx: "84", cy: "55", r: "3.2", fill: "#BAE6FD", class: "spidey-lens" }),
    // Cute chibi blush
    svgEl("ellipse", { cx: "29", cy: "74", rx: "4.8", ry: "2.6", fill: "#FF9EBB", opacity: "0.75" }),
    svgEl("ellipse", { cx: "91", cy: "74", rx: "4.8", ry: "2.6", fill: "#FF9EBB", opacity: "0.75" }),
    // Customer service headset & mic boom
    svgEl("rect", { x: "14", y: "54", width: "7", height: "15", rx: "3.5", fill: "#FFD000", stroke: "#18191F", "stroke-width": "2.4" }),
    svgEl("path", { d: "M17 68 Q27 85 49 84", stroke: "#18191F", "stroke-width": "2.6", fill: "none", "stroke-linecap": "round" }),
    svgEl("circle", { cx: "51", cy: "84", r: "3.8", fill: "#FFD000", stroke: "#18191F", "stroke-width": "2" })
  );
  return svg;
}

function icon(name, className) {
  const holder = el("span", className);
  holder.dataset.icon = name;
  holder.setAttribute("aria-hidden", "true");
  drawIcon(holder);
  return holder;
}

function drawIcon(holder) {
  if (holder.dataset.icon === "spidey" || holder.classList.contains("brand-symbol") || holder.classList.contains("service-avatar")) {
    holder.replaceChildren(spideySvg(true));
    return;
  }
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  for (const d of ICONS[holder.dataset.icon] || ICONS.info) {
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", d);
    svg.append(path);
  }
  holder.replaceChildren(svg);
}

async function api(path, body) {
  const init = { headers: { Accept: "application/json" }, credentials: "same-origin" };
  if (body !== undefined) {
    init.method = "POST";
    if (body instanceof FormData) init.body = body;
    else {
      init.headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(body);
    }
  }
  let response;
  try {
    response = await fetch(path, init);
  } catch (_) {
    connectionState(false);
    throw new Error("连接中断，请稍后重试。");
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const error = new Error((data && data.message) || `请求失败（HTTP ${response.status}）`);
    error.status = response.status;
    throw error;
  }
  connectionState(true);
  return data;
}

function connectionState(connected) {
  const node = $("connection");
  if (!node) return;
  node.classList.toggle("connected", connected);
  node.classList.toggle("offline", !connected);
  node.lastElementChild.textContent = connected ? "已连接" : "连接中断";
  node.title = connected ? "已连接" : "连接中断";
  node.setAttribute("aria-label", node.title);
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}

function button(label, className, onClick) {
  const node = el("button", className, label);
  node.type = "button";
  node.addEventListener("click", onClick);
  return node;
}

function factRows(rows) {
  return rows.flatMap(([label, value]) => [el("dt", "", label), el("dd", "", value)]);
}

function facts(rows) {
  const list = el("dl", "facts");
  list.append(...factRows(rows));
  return list;
}

function badge(status) {
  return el("span", `badge badge-${status}`, STATUS_TEXT[status] || status);
}

function attachmentList(items, { customer = false } = {}) {
  const list = el("div", "attachment-list");
  for (const item of items || []) {
    const card = el("div", `attachment-card attachment-${item.kind}`);
    card.append(icon(item.kind === "image" ? "image" : "audio"), el("div", "attachment-info"));
    const info = card.lastElementChild;
    info.append(el("strong", "", item.original_name || (item.kind === "image" ? "图片附件" : "语音附件")),
      el("small", "", item.kind === "image" ? "图片 · 仅供人工客服查看" : "语音 · 仅供人工客服播放"));
    if (item.kind === "image") {
      const preview = document.createElement("img");
      preview.src = item.url;
      preview.alt = item.original_name || "顾客上传的图片";
      preview.loading = "lazy";
      card.append(preview);
    } else {
      const player = document.createElement("audio");
      player.controls = true;
      player.preload = "metadata";
      player.src = item.url;
      card.append(player);
    }
    list.append(card);
  }
  if (items && items.length) {
    const note = el("p", "attachment-disclosure", customer ? "附件已发送给人工客服，AI 不会自动识别其中内容。" : "顾客声明：附件由人工客服查看，AI 未自动识别。 ");
    list.append(note);
  }
  return list;
}

function delayText(seconds) {
  if (seconds <= 0) return "没有晚到";
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return rest ? `${minutes} 分钟 ${rest} 秒` : `${minutes} 分钟`;
}

function clock(iso) {
  return iso ? iso.slice(11, 19) : "";
}

function showStatus(text, isError) {
  const node = $("status");
  if (!node) return;
  node.textContent = text || "";
  node.classList.toggle("error", Boolean(isError));
}

function renderMeta(info) {
  const policy = info.policy;
  const rule = policy.include_threshold ? `晚到 ${policy.threshold_minutes} 分钟及以上` : `晚到超过 ${policy.threshold_minutes} 分钟`;
  $("meta").textContent = "演示";
  $("policy-details").replaceChildren(...factRows([
    ["规则版本", policy.version], ["申请条件", `已送达且${rule}`],
    ["建议补偿", `¥${policy.coupon_yuan} 模拟券，人工审核后发放`],
    ["对话模式", info.model_mode === "live" ? "在线模型" : "固定脚本"],
    ["模型", info.model], ["订单版本", info.data_version], ["模拟日期", info.service_date],
  ]));
  if ($("guide-policy")) $("guide-policy").textContent = `已送达，${rule}可申请`;
  if ($("guide-amount")) $("guide-amount").textContent = `¥${policy.coupon_yuan}`;
}

function renderLogin(people, idKey, onPick) {
  const names = { U001: "顾客 01", U002: "顾客 02", R001: "商家账号" };
  $("login-choices").replaceChildren(...people.map((person) => {
    const node = button("", "login-option", async () => {
      const choices = [...$("login-choices").querySelectorAll("button")];
      for (const choice of choices) choice.disabled = true;
      try { await onPick(person[idKey]); }
      finally { for (const choice of choices) choice.disabled = false; }
    });
    node.setAttribute("aria-label", person.display_name);
    const text = el("div");
    text.append(el("strong", "", names[person[idKey]] || person.display_name), el("small", "", person[idKey]));
    node.append(el("span", "avatar", person[idKey]), text, icon("arrow-right"));
    return node;
  }));
}

function setSignedIn(name) {
  if (!name) openHistories.clear();
  $("who-name").textContent = name ? name.replace(/^模拟顾客 /, "顾客 ").replace(/^模拟审批员 /, "商家 ") : "";
  $("who").hidden = !name;
  $("app").hidden = !name;
  $("login").hidden = Boolean(name);
  if ($("quick-scenarios")) $("quick-scenarios").hidden = !name;
  if ($("reset")) $("reset").hidden = !name;
  document.body.classList.toggle("is-signed-in", Boolean(name));
}

function careBuddy(className = "") {
  const buddy = el("span", `care-buddy ${className}`.trim());
  buddy.setAttribute("aria-hidden", "true");
  buddy.append(spideySvg(false));
  return buddy;
}

function emptyState(symbol, heading, message, large = false) {
  const box = el("div", large ? "empty-state empty" : "empty-illustration empty");
  box.append(careBuddy(large ? "buddy-empty" : "buddy-compact"));
  const text = el("div");
  text.append(el(large ? "h3" : "strong", "", heading));
  if (message) text.append(el("p", "", message));
  box.append(text);
  return box;
}

const openHistories = new Set();

function ticketHistory(ticketId) {
  const details = el("details", "ticket-history");
  details.dataset.ticketHistory = ticketId;
  const summary = el("summary", "history-summary", "处理记录");
  summary.append(icon("chevron-down"));
  const list = el("ol", "history-list");
  details.append(summary, list);
  let loading = false;
  const load = async () => {
    if (loading) return;
    loading = true;
    list.setAttribute("aria-busy", "true");
    list.replaceChildren(el("li", "history-loading", "读取中…"));
    try {
      const role = document.body.dataset.page === "review" ? "review" : "customer";
      const data = await api(`/api/${role}/tickets/${encodeURIComponent(ticketId)}`);
      if (!details.open || !details.isConnected) return;
      const entries = data.timeline || data.events || [];
      const labels = { submitted: "已提交", information_requested: "商家提问", information_submitted: "已补充", approved: "审核通过", rejected: "未通过", rated: "顾客评价" };
      list.replaceChildren(...entries.map((entry) => {
        const row = el("li", "history-event");
        const head = el("div", "history-event-head");
        head.append(el("strong", "", labels[entry.action] || "更新"), el("time", "", clock(entry.at)));
        row.append(head);
        if (entry.note) row.append(el("p", "", entry.note));
        return row;
      }));
      if (!entries.length) list.append(el("li", "history-loading", "暂无记录"));
    } catch (error) {
      if (!details.open || !details.isConnected) return;
      const row = el("li", "history-error", error.message);
      row.append(button("重试", "history-retry", load));
      list.replaceChildren(row);
    } finally { loading = false; list.removeAttribute("aria-busy"); }
  };
  details.addEventListener("toggle", () => {
    if (details.open) { openHistories.add(ticketId); load(); }
    else openHistories.delete(ticketId);
  });
  details.open = openHistories.has(ticketId);
  return details;
}

function startPolling(refresh, ms) {
  let running = false;
  const tick = async () => {
    if (running || document.hidden) return;
    running = true;
    try { await refresh(); }
    catch (error) { showStatus(error.message, true); }
    finally { running = false; }
  };
  setInterval(tick, ms);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) tick(); });
}

function bootUI() {
  document.querySelectorAll("[data-icon]").forEach(drawIcon);
  document.querySelectorAll(".floating-receipt .receipt-symbol").forEach((node) => node.replaceChildren(spideySvg(false)));
  let theme;
  try { theme = localStorage.getItem("delivery-care-theme"); } catch (_) { /* Theme is optional. */ }
  if (theme === "light" || theme === "dark") document.documentElement.dataset.theme = theme;
  const applyThemeIcon = () => {
    const dark = document.documentElement.dataset.theme === "dark" ||
      (!document.documentElement.dataset.theme && window.matchMedia("(prefers-color-scheme: dark)").matches);
    $("theme-toggle").replaceChildren(icon(dark ? "sun" : "moon"));
    $("theme-toggle").setAttribute("aria-label", dark ? "切换浅色主题" : "切换深色主题");
  };
  applyThemeIcon();
  $("theme-toggle").addEventListener("click", () => {
    const dark = $("theme-toggle").getAttribute("aria-label") === "切换浅色主题";
    const next = dark ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("delivery-care-theme", next); } catch (_) { /* Works without storage. */ }
    applyThemeIcon();
  });
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", applyThemeIcon);
  document.querySelectorAll("[data-open-demo]").forEach((node) => node.addEventListener("click", () => $("demo-dialog").showModal()));
  document.querySelectorAll("[data-close-dialog]").forEach((node) => node.addEventListener("click", () => node.closest("dialog").close()));
  document.querySelectorAll("dialog").forEach((dialog) => dialog.addEventListener("click", (event) => {
    if (event.target !== dialog) return;
    const rect = dialog.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
  }));
}

bootUI();
