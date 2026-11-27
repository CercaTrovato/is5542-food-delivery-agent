// ORD001 bilingual layer: one-click 中文 / English switch for the customer and merchant consoles.
// The app keeps producing its canonical Chinese text; this layer translates what is displayed
// (text nodes + accessible attributes) from a reviewed dictionary, and restores Chinese on switch-back.
"use strict";
(() => {
  const STORAGE_KEY = "ord001_ui_lang";
  const CJK = /[\u4e00-\u9fff]/;
  const params = new URLSearchParams(location.search);
  const fromUrl = params.get("lang");
  let lang = fromUrl === "en" || fromUrl === "zh" ? fromUrl : (localStorage.getItem(STORAGE_KEY) === "en" ? "en" : "zh");
  if (fromUrl === "en" || fromUrl === "zh") {
    try { localStorage.setItem(STORAGE_KEY, lang); } catch (_) {}
  }

  const DICT = window.ORD001_I18N_DICT || { exact: {}, templates: [] };
  const exact = new Map(Object.entries(DICT.exact).map(([k, v]) => [k.trim(), v]));
  // Dish names also appear without their quantity suffix (e.g. order-card thumbnails).
  for (const [k, v] of [...exact]) {
    const m = /^(.+?)\s*×\s*\d+$/.exec(k);
    if (m && !exact.has(m[1])) exact.set(m[1], v.replace(/\s*×\s*\d+$/, ""));
  }
  // Proper nouns that may sit inside otherwise-English model replies.
  const NAMES = new Map(Object.entries(DICT.names || {}));
  for (const [k, v] of exact) if (/^.+?\s*×\s*\d+$/.test(k) === false && /饭|面|茶|汤|翅|鸽|水$/.test(k) && k.length <= 12) NAMES.set(k, v);
  const nameKeys = [...NAMES.keys()].sort((a, b) => b.length - a.length);
  const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const nameRe = nameKeys.length ? new RegExp(nameKeys.map(escapeRe).join("|"), "g") : null;
  // A dynamic value never spans sentences, except a free-text value that follows a label ending in "："/"】".
  const rules = DICT.templates
    .map(([zh, en]) => {
      const parts = zh.split("{}");
      const free = [];
      const body = parts.map((part, i) => {
        if (i === 0) return escapeRe(part);
        const prev = parts[i - 1];
        const isFree = /[：】]$/.test(prev) || (i === parts.length - 1 && part === "" && /[：】]\s*$/.test(prev));
        free.push(isFree);
        return (isFree ? "([\\s\\S]*?)" : "([^。！？\\n]*?)") + escapeRe(part);
      }).join("");
      return { re: new RegExp("^" + body + "$"), en, free, weight: parts.join("").length };
    })
    .sort((a, b) => b.weight - a.weight);
  const phraseKeys = [...exact.keys()].filter((k) => k.length >= 2 && CJK.test(k)).sort((a, b) => b.length - a.length);
  const phraseRe = phraseKeys.length ? new RegExp(phraseKeys.map(escapeRe).join("|"), "g") : null;
  const PREFIX_RE = /^([•·\-\s]+|(?:[\u2600-\u27BF]|[\uD83C-\uDBFF][\uDC00-\uDFFF])\uFE0F?\s*)/;
  const SEP_RE = /(\s·\s|｜|\s\|\s|、|\s\/\s|\s→\s)/;
  const cache = new Map();

  function asciiPunct(s) {
    if (CJK.test(s)) return s;
    return s
      .replace(/（/g, " (").replace(/）/g, ") ").replace(/：/g, ": ").replace(/；/g, "; ")
      .replace(/，/g, ", ").replace(/。/g, ". ").replace(/！/g, "! ").replace(/？/g, "? ")
      .replace(/「|」|『|』/g, "\"").replace(/【/g, "[").replace(/】/g, "] ")
      .replace(/ {2,}/g, " ").replace(/\( /g, "(").replace(/ \)/g, ")").replace(/ ([,.;:!?)\]])/g, "$1")
      .replace(/\s+$/g, (m) => (m.includes("\n") ? m : ""));
  }

  // Exact dictionary hit or a full template match; null when the text is unknown.
  function whole(text, strict) {
    const t = text.trim();
    if (!t) return text;
    if (!CJK.test(t)) return text;
    let hit = exact.get(t);
    if (hit === undefined) {
      for (const r of rules) {
        const m = r.re.exec(t);
        if (!m) continue;
        const groups = m.slice(1).map((g, gi) => {
          const out = tr(g || "", strict);
          return { out, bad: !r.free[gi] && CJK.test(out) };
        });
        if (strict && groups.some((g) => g.bad)) continue;
        hit = r.en.replace(/\{(\d+)\}/g, (_, i) => (groups[Number(i)] ? groups[Number(i)].out : ""));
        break;
      }
    }
    if (hit === undefined) {
      const pm = PREFIX_RE.exec(t);
      if (pm && pm[0].length < t.length) {
        const rest = whole(t.slice(pm[0].length), strict);
        if (rest !== null) hit = pm[0] + rest.trim();
      }
    }
    if (hit === undefined || hit === null) return null;
    const lead = text.match(/^\s*/)[0];
    const trail = text.match(/\s*$/)[0];
    return lead + hit + trail;
  }

  function bySeparators(text, strict) {
    if (!SEP_RE.test(text)) return null;
    const parts = text.split(SEP_RE);
    let ok = true;
    const out = parts.map((p, idx) => {
      if (idx % 2 === 1) return p === "、" ? ", " : p;
      if (!CJK.test(p)) return p;
      const w = whole(p, strict);
      if (w === null) { ok = false; return p; }
      return w;
    });
    return ok ? out.join("") : null;
  }

  function phraseFallback(text) {
    if (!phraseRe) return text;
    return text.replace(phraseRe, (m) => exact.get(m) + " ");
  }

  function translateRuns(text, strict) {
    const pieces = text.match(/[^。！？；\n]+[。！？；]?|\n/g) || [text];
    const out = [];
    let failed = false;
    let i = 0;
    while (i < pieces.length) {
      const p = pieces[i];
      if (p === "\n" || !CJK.test(p)) { out.push(p); i++; continue; }
      let matched = false;
      for (let j = pieces.length; j > i; j--) {
        const slice = pieces.slice(i, j);
        if (slice.includes("\n")) continue;
        const chunk = slice.join("");
        const w = whole(chunk, strict) ?? (j === i + 1 ? bySeparators(chunk, strict) : null);
        if (w !== null) { out.push(w); i = j; matched = true; break; }
      }
      if (!matched) {
        failed = true;
        out.push(strict ? p : phraseFallback(p));
        i++;
      }
    }
    if (failed && strict) return text;
    let joined = "";
    for (const seg of out) {
      if (joined && !/\s$/.test(joined) && seg !== "\n" && !/^\s/.test(seg) && /[.!?:;)]$/.test(joined)) joined += " ";
      joined += seg;
    }
    return joined;
  }

  function tr(text, strict = false) {
    if (lang !== "en" || typeof text !== "string" || !CJK.test(text)) return text;
    const key = (strict ? "1" : "0") + text;
    if (cache.has(key)) return cache.get(key);
    let out = whole(text, strict);
    if (out === null) out = translateRuns(text, strict);
    if (CJK.test(out) && nameRe && /[a-z]{3,}/i.test(out)) out = out.replace(nameRe, (m) => NAMES.get(m));
    out = asciiPunct(out);
    cache.set(key, out);
    return out;
  }

  // ---- DOM application -------------------------------------------------------------------------
  const TEXT_STATE = new WeakMap();
  const ATTR_STATE = new WeakMap();
  const ATTRS = ["title", "aria-label", "placeholder", "alt"];
  const STRICT_SEL = ".bubble, .handoff-transcript p, .ticket-note p, .information-request p, .typing-text";
  const SKIP_SEL = "script, style, textarea, [data-i18n-skip]";

  function handleText(node) {
    const parent = node.parentElement;
    if (!parent || parent.closest(SKIP_SEL)) return;
    const cur = node.data;
    let st = TEXT_STATE.get(node);
    if (st && cur === st.out) {
      if (st.lang === lang) return;
    } else {
      if (!CJK.test(cur) && lang === "zh") { TEXT_STATE.delete(node); return; }
      st = { src: cur };
    }
    const out = lang === "en" ? tr(st.src, Boolean(parent.closest(STRICT_SEL))) : st.src;
    st.out = out;
    st.lang = lang;
    TEXT_STATE.set(node, st);
    if (out !== cur) node.data = out;
  }

  function handleAttr(el, name) {
    if (!el.hasAttribute(name) || el.closest("[data-i18n-skip], script, style")) return;
    const cur = el.getAttribute(name);
    let map = ATTR_STATE.get(el);
    if (!map) { map = {}; ATTR_STATE.set(el, map); }
    let st = map[name];
    if (st && cur === st.out) {
      if (st.lang === lang) return;
    } else {
      if (!CJK.test(cur) && lang === "zh") { delete map[name]; return; }
      st = { src: cur };
    }
    const out = lang === "en" ? tr(st.src) : st.src;
    st.out = out;
    st.lang = lang;
    map[name] = st;
    if (out !== cur) el.setAttribute(name, out);
  }

  function processTree(root) {
    if (!root) return;
    if (root.nodeType === Node.TEXT_NODE) { handleText(root); return; }
    if (root.nodeType !== Node.ELEMENT_NODE) return;
    if (root.matches && root.matches("script, style")) return;
    for (const a of ATTRS) if (root.hasAttribute(a)) handleAttr(root, a);
    if (root.tagName === "TEXTAREA" || root.tagName === "INPUT") return;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
    let n = walker.nextNode();
    while (n) {
      if (n.nodeType === Node.TEXT_NODE) handleText(n);
      else for (const a of ATTRS) if (n.hasAttribute(a)) handleAttr(n, a);
      n = walker.nextNode();
    }
  }

  const observer = new MutationObserver((mutations) => {
    for (const m of mutations) {
      if (m.type === "childList") m.addedNodes.forEach(processTree);
      else if (m.type === "characterData") handleText(m.target);
      else if (m.type === "attributes" && m.attributeName) handleAttr(m.target, m.attributeName);
    }
  });

  // ---- Toggle ----------------------------------------------------------------------------------
  function paintToggle(btn) {
    btn.textContent = lang === "en" ? "中文" : "EN";
    btn.setAttribute("aria-label", lang === "en" ? "切换到中文" : "Switch to English");
    btn.title = lang === "en" ? "切换到中文 / Switch to Chinese" : "Switch to English / 切换到英文";
    btn.setAttribute("aria-pressed", String(lang === "en"));
  }

  function mountToggle() {
    for (const bar of document.querySelectorAll(".topbar-actions")) {
      if (bar.querySelector(".lang-toggle")) continue;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "icon-button lang-toggle";
      btn.dataset.i18nSkip = "";
      btn.addEventListener("click", () => setLang(lang === "en" ? "zh" : "en"));
      paintToggle(btn);
      const theme = bar.querySelector("#theme-toggle");
      bar.insertBefore(btn, theme || bar.firstChild);
    }
  }

  function setLang(next) {
    lang = next === "en" ? "en" : "zh";
    try { localStorage.setItem(STORAGE_KEY, lang); } catch (_) {}
    document.documentElement.lang = lang === "en" ? "en" : "zh-CN";
    document.querySelectorAll(".lang-toggle").forEach(paintToggle);
    processTree(document.documentElement);
    window.dispatchEvent(new CustomEvent("ord001:langchange", { detail: { lang } }));
  }

  window.ORD001_I18N = {
    get lang() { return lang; },
    isEn: () => lang === "en",
    t: (s) => tr(s),
    setLang,
  };

  function start() {
    document.documentElement.lang = lang === "en" ? "en" : "zh-CN";
    mountToggle();
    processTree(document.documentElement);
    observer.observe(document.documentElement, {
      subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ATTRS,
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
