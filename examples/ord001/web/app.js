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
};

function icon(name, className) {
  const holder = el("span", className);
  holder.dataset.icon = name;
  holder.setAttribute("aria-hidden", "true");
  drawIcon(holder);
  return holder;
}

function drawIcon(holder) {
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
    init.headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(body);
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
  const buddy = el("span", `care-buddy ${className}`);
  buddy.setAttribute("aria-hidden", "true");
  const face = el("span", "buddy-face");
  face.append(el("i"), el("i"), el("span"));
  buddy.append(el("span", "buddy-handle"), face, icon("bowl", "buddy-emblem"));
  return buddy;
}

function emptyState(symbol, heading, message, large = false) {
  const box = el("div", large ? "empty-state empty" : "empty-illustration empty");
  box.append(large ? careBuddy("buddy-empty") : icon(symbol));
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
      const labels = { submitted: "已提交", information_requested: "商家提问", information_submitted: "已补充", approved: "审核通过", rejected: "未通过" };
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
