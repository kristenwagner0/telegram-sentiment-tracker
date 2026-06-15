/**
 * SentimentTrack dashboard client — navigation, charts, CSV parsing, Google Sheets load.
 * Purpose: Interactive UI for community sentiment analytics; runs entirely in the browser.
 * Deploy:  Served as static files by server.py (local + Render). No build step required.
 */

const COLORS = {
  pos: "#5E8B7E",
  neg: "#9B6B6B",
  neu: "#8E8E93",
  net: "#8B9EC4",
  posBg: "rgba(94,139,126,.12)",
  negBg: "rgba(155,107,107,.12)",
  neuBg: "rgba(142,142,147,.1)",
  netBg: "rgba(139,158,196,.08)",
};

const SERIES_INDEX = { pos: 0, neg: 1, neu: 2, net: 3 };

let lang = "ko";
let currentWeek = 0;
let lineChart = null;
let currentRange = "monthly";
let currentWindow = { weekly: "52w", monthly: "all", yearly: "all" };

const CHART_WINDOWS = {
  weekly: [
    { id: "12w", label: "3 months", n: 12 },
    { id: "26w", label: "6 months", n: 26 },
    { id: "52w", label: "1 year", n: 52 },
    { id: "all", label: "All", n: Infinity },
  ],
  monthly: [
    { id: "6m", label: "6 months", n: 6 },
    { id: "12m", label: "1 year", n: 12 },
    { id: "24m", label: "2 years", n: 24 },
    { id: "all", label: "All", n: Infinity },
  ],
  yearly: [
    { id: "3y", label: "3 years", n: 3 },
    { id: "5y", label: "5 years", n: 5 },
    { id: "all", label: "All", n: Infinity },
  ],
};
let dataSource = "demo";
let portfolioMode = false;
let embedMode = false;
let appConfig = { repoUrl: "https://github.com/kristenwagner0/telegram-sentiment-tracker", contactEmail: "" };
let rawMessages = [];
let chartKeys = { monthly: [], weekly: [], yearly: [] };
let isTranslating = false;
const translationCache = JSON.parse(localStorage.getItem("st_translations_v2") || "{}");
const COMPLAINERS_DEMO_PW = "CommunityReview2026";
const COMPLAINERS_UNLOCK_KEY = "st_complainers_unlocked";

const PORTFOLIO_EVENTS = [
  { id: 1, date: "2021-06-08", label: "Bridge outage", type: "neg" },
  { id: 2, date: "2022-12-13", label: "Validator incident", type: "neg" },
  { id: 3, date: "2023-09-18", label: "Testnet milestone", type: "pos" },
  { id: 4, date: "2024-04-02", label: "Mainnet launch", type: "pos" },
  { id: 5, date: "2024-10-07", label: "Network instability", type: "neg" },
  { id: 6, date: "2025-06-09", label: "Governance AMA", type: "pos" },
];
const PORTFOLIO_EVENTS_KEY = "st_events_portfolio_v1";

let events = JSON.parse(localStorage.getItem("st_events") || "null") || [...PORTFOLIO_EVENTS];
let nextId = Math.max(0, ...events.map((e) => e.id)) + 1;

function seedPortfolioEvents(force = false) {
  if (!force && localStorage.getItem(PORTFOLIO_EVENTS_KEY) === "1") return;
  events = PORTFOLIO_EVENTS.map((e) => ({ ...e }));
  nextId = events.length + 1;
  localStorage.setItem("st_events", JSON.stringify(events));
  localStorage.setItem(PORTFOLIO_EVENTS_KEY, "1");
  renderEventList();
  renderAnnotations();
}

const typeConfig = {
  neg: { color: COLORS.neg, bg: COLORS.negBg, label: "Incident" },
  pos: { color: COLORS.pos, bg: COLORS.posBg, label: "Positive" },
  neu: { color: COLORS.neu, bg: COLORS.neuBg, label: "Announcement" },
  acc: { color: COLORS.net, bg: COLORS.netBg, label: "Other" },
};

const NAV = {
  dashboard: { title: "Dashboard", mode: "community" },
  trends: { title: "Trends", mode: "community" },
  complaints: { title: "Complaints", mode: "community" },
  messages: { title: "Messages", mode: "community" },
  sheets: { title: "Google Sheets", mode: "community" },
  upload: { title: "Analyze my chat", mode: "upload" },
  gettool: { title: "Get the tool", mode: "community" },
  settings: { title: "Settings", mode: "community" },
};

const DEMO_SENTIMENT_EVENTS = [
  ["2021-05-03", "2021-07-12", -11, 13],
  ["2022-10-17", "2023-02-06", -16, 20],
  ["2023-08-21", "2023-10-09", 15, -11],
  ["2024-02-26", "2024-05-20", 20, -14],
  ["2024-09-16", "2024-11-04", -12, 15],
  ["2025-05-05", "2025-07-21", 14, -10],
];

function demoEventStrength(isoDate, start, end) {
  const ws = new Date(isoDate).getTime();
  const s = new Date(start).getTime();
  const e = new Date(end).getTime();
  if (ws < s || ws > e) return 0;
  const mid = (s + e) / 2;
  const half = Math.max((e - s) / 2, 86400000);
  return Math.max(0, 1 - Math.abs(ws - mid) / half);
}

function demoEventModifier(isoDate) {
  let posD = 0;
  let negD = 0;
  for (const [start, end, pd, nd] of DEMO_SENTIMENT_EVENTS) {
    const strength = demoEventStrength(isoDate, start, end);
    if (strength) {
      posD += (pd / 100) * strength;
      negD += (nd / 100) * strength;
    }
  }
  return { posD, negD };
}

function demoTrendPct(i, total, startPos, endPos, startNeg, endNeg, isoDate) {
  const t = total <= 1 ? 0 : i / (total - 1);
  let pos = startPos + (endPos - startPos) * t + Math.sin(i * 0.7) * 2;
  let neg = startNeg + (endNeg - startNeg) * t + Math.cos(i * 0.5) * 2;
  if (isoDate) {
    const { posD, negD } = demoEventModifier(isoDate);
    pos += posD * 100;
    neg += negD * 100;
  }
  const neu = Math.max(5, 100 - pos - neg);
  const adjPos = 100 - neg - neu;
  return {
    pos: Math.round(Math.max(8, Math.min(78, adjPos))),
    neg: Math.round(Math.max(8, Math.min(62, neg))),
    neu: Math.round(neu),
    net: Math.round(((adjPos - neg) / 100) * 100) / 100,
  };
}

function buildDemoData() {
  const TOTAL_WEEKS = 326;
  const topics = [
    "Wallet sync issues",
    "Gas fees too high",
    "Bridge delays",
    "Staking UI confusion",
    "Testnet faucet errors",
  ];

  const monthlyKeys = [];
  for (let y = 2020; y <= 2026; y++) {
    const startM = y === 2020 ? 3 : 1;
    const endM = y === 2026 ? 6 : 12;
    for (let m = startM; m <= endM; m++) {
      monthlyKeys.push(`${y}-${String(m).padStart(2, "0")}`);
    }
  }
  const monthlyLabels = monthlyKeys.map((k) => {
    const [y, mo] = k.split("-");
    return new Date(y, mo - 1).toLocaleString("en", { month: "short", year: "numeric" });
  });
  const monthlyPos = [];
  const monthlyNeg = [];
  const monthlyNeu = [];
  const monthlyNet = [];
  monthlyKeys.forEach((_, i) => {
    const s = demoTrendPct(i, monthlyKeys.length, 35, 58, 38, 22, `${monthlyKeys[i]}-01`);
    monthlyPos.push(s.pos);
    monthlyNeg.push(s.neg);
    monthlyNeu.push(s.neu);
    monthlyNet.push(s.net);
  });

  const wkLabels = [];
  const wkKeys = [];
  const wkPos = [];
  const wkNeg = [];
  const wkNeu = [];
  const wkNet = [];
  const weeks52 = [];
  const complaints52 = [];
  const baseDate = new Date(2020, 2, 10);
  for (let i = 0; i < TOTAL_WEEKS; i++) {
    const d = new Date(baseDate);
    d.setDate(d.getDate() + i * 7);
    const iso = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    wkKeys.push(iso);
    weeks52.push(d.toLocaleDateString("en", { month: "short", day: "numeric", year: "numeric" }));
    wkLabels.push(d.toLocaleString("en", { month: "short", day: "numeric", year: "numeric" }));
    const s = demoTrendPct(i, TOTAL_WEEKS, 35, 58, 38, 22, iso);
    wkPos.push(s.pos);
    wkNeg.push(s.neg);
    wkNeu.push(s.neu);
    wkNet.push(s.net);
    complaints52.push(
      topics.slice(0, 5).map((t, j) => ({ t, tEn: "", n: Math.max(2, 18 - j * 3 - (i % 4)) }))
    );
  }

  const yearlyKeys = ["2020", "2021", "2022", "2023", "2024", "2025", "2026"];
  const yearlyPos = [];
  const yearlyNeg = [];
  const yearlyNeu = [];
  const yearlyNet = [];
  yearlyKeys.forEach((_, i) => {
    const s = demoTrendPct(i, yearlyKeys.length, 35, 58, 38, 22, `${yearlyKeys[i]}-06-01`);
    yearlyPos.push(s.pos);
    yearlyNeg.push(s.neg);
    yearlyNeu.push(s.neu);
    yearlyNet.push(s.net);
  });

  return {
    chartData: {
      monthly: { labels: monthlyLabels, keys: monthlyKeys, pos: monthlyPos, neg: monthlyNeg, neu: monthlyNeu, net: monthlyNet },
      weekly: { labels: wkLabels, keys: wkKeys, pos: wkPos, neg: wkNeg, neu: wkNeu, net: wkNet },
      yearly: { labels: yearlyKeys, keys: yearlyKeys, pos: yearlyPos, neg: yearlyNeg, neu: yearlyNeu, net: yearlyNet },
    },
    chartKeys: {
      monthly: monthlyKeys,
      weekly: wkKeys,
      yearly: yearlyKeys,
    },
    weeks52,
    complaints52,
    complainers: [
      { initials: "NV", color: COLORS.neg, bg: COLORS.negBg, name: "NovaTrader218", msgs: 12, topics: "Bridge delays, gas fees" },
      { initials: "MK", color: COLORS.neu, bg: COLORS.neuBg, name: "MinjiValidator91", msgs: 8, topics: "Staking UI, docs" },
    ],
    responseData: [
      { label: "Calming responses", sub: "Threads that quieted after admin reply", color: "var(--pos)", badge: "62%", badgeBg: "var(--pos-bg)", badgeColor: "var(--pos)" },
      { label: "Escalating responses", sub: "More negative messages after reply", color: "var(--neg)", badge: "18%", badgeBg: "var(--neg-bg)", badgeColor: "var(--neg)" },
      { label: "No measurable effect", sub: "Sentiment unchanged after reply", color: "var(--text3)", badge: "20%", badgeBg: "var(--card2)", badgeColor: "var(--text2)" },
    ],
    posThemes: [
      { text: "Helix mainnet upgrade", textEn: "", n: 87 },
      { text: "Community helpfulness", textEn: "", n: 74 },
      { text: "Useful governance updates", textEn: "", n: 61 },
    ],
    recentMsgs: [
      { date: "Jun 4", text: "헬릭스 메인넷 업그레이드 정말 매끄럽게 진행됐어요!", text_en: "", s: "pos" },
      { date: "Jun 3", text: "브릿지 처리 대기 시간이 너무 길어요.", text_en: "", s: "neg" },
      { date: "Jun 3", text: "다음 AMA 일정 공지 확인했습니다.", text_en: "", s: "neu" },
    ],
    summary: { total: 134971, posPct: 50, negPct: 28, neuPct: 22, weekMsgs: 414, weekPos: 54, weekNeg: 24, weekNeu: 22 },
  };
}


const demo = buildDemoData();

let chartData = { ...demo.chartData };
let weeks52 = [...demo.weeks52];
let complaints52 = [...demo.complaints52];
let complainers = [...demo.complainers];
let responseData = [...demo.responseData];
let posThemes = [...demo.posThemes];
let recentMsgs = [...demo.recentMsgs];
let summary = { ...demo.summary };

// ── Navigation ───────────────────────────────────────────────────────
function isNavVisible(page) {
  const el = document.querySelector(`.sidebar .nav-item[data-nav="${page}"]`);
  if (!el) return false;
  return getComputedStyle(el).display !== "none";
}

function syncMobileNav(page) {
  document.querySelectorAll(".mobile-nav-tab").forEach((el) => {
    el.classList.toggle("active", el.dataset.nav === page);
  });
}

function buildMobileNav() {
  const container = document.getElementById("mobileNav");
  if (!container) return;
  container.innerHTML = "";
  document.querySelectorAll(".sidebar .nav-item[data-nav]").forEach((el) => {
    if (getComputedStyle(el).display === "none") return;
    const page = el.dataset.nav;
    if (!NAV[page]) return;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "mobile-nav-tab";
    btn.dataset.nav = page;
    btn.textContent = NAV[page].title;
    if (page === "complaints" && el.querySelector(".nav-badge")) {
      const dot = document.createElement("span");
      dot.className = "mobile-nav-dot";
      dot.setAttribute("aria-hidden", "true");
      btn.appendChild(dot);
    }
    btn.addEventListener("click", () => navigate(page));
    if (el.classList.contains("active")) btn.classList.add("active");
    container.appendChild(btn);
  });
}

function applyInitialPanel() {
  const panel = new URLSearchParams(window.location.search).get("panel");
  if (panel && NAV[panel] && isNavVisible(panel)) navigate(panel);
}

function navigate(page) {
  if (!NAV[page]) return;
  document.querySelectorAll(".nav-item[data-nav]").forEach((el) => {
    el.classList.toggle("active", el.dataset.nav === page);
  });
  document.querySelectorAll(".panel").forEach((el) => el.classList.remove("active"));
  document.getElementById(`panel-${page}`)?.classList.add("active");
  document.getElementById("pageTitle").textContent = NAV[page].title;
  setMode(NAV[page].mode, null, false);
  syncMobileNav(page);
  if (page === "trends") setTimeout(renderAnnotations, 120);
}

function setMode(m, btn, updatePanels = true) {
  document.querySelectorAll(".mode-btn").forEach((b) => {
    if (btn) b.classList.toggle("active", b === btn);
    else b.classList.toggle("active", b.dataset.mode === m);
  });
  if (updatePanels) {
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
    const target = m === "upload" ? "panel-upload" : "panel-dashboard";
    document.getElementById(target)?.classList.add("active");
    document.querySelectorAll(".nav-item[data-nav]").forEach((el) => {
      el.classList.toggle("active", el.dataset.nav === (m === "upload" ? "upload" : "dashboard"));
    });
    syncMobileNav(m === "upload" ? "upload" : "dashboard");
  }
  updateModeDesc(m);
}

function updateModeDesc(modeOverride) {
  const m =
    modeOverride ||
    (document.querySelector(".mode-btn.active")?.dataset.mode === "upload" ? "upload" : "community");
  let text;
  if (m === "upload") {
    text = "Run sentiment analysis locally · this hosted page is the viewer only";
  } else if (dataSource === "portfolio") {
    text = `Illustrative demo · fictional Helix Protocol · ${summary.total.toLocaleString()} synthetic messages`;
  } else if (dataSource === "sheet") {
    text = "Live data from Google Sheets · refresh to update";
  } else if (dataSource === "csv") {
    text = `Your CSV · ${summary.total.toLocaleString()} messages loaded in this browser session`;
  } else {
    text = portfolioMode
      ? "Illustrative demo · fictional Helix Protocol community · source on GitHub"
      : "Demo preview · connect Google Sheets in the sidebar for live data";
  }
  document.getElementById("modeDescText").textContent = text;
}

function applyPortfolioNav() {
  document.getElementById("nav-sheets")?.style.setProperty("display", "none");
  document.getElementById("nav-upload")?.style.setProperty("display", "none");
  document.getElementById("nav-gettool")?.style.setProperty("display", "");
  document.querySelector(".mode-pill")?.style.setProperty("display", embedMode ? "none" : "");
  const repo = appConfig.repoUrl || "https://github.com/kristenwagner0/telegram-sentiment-tracker";
  const repoEl = document.getElementById("gettoolRepoLink");
  if (repoEl) repoEl.href = repo;
  const cloneEl = document.getElementById("gettoolCloneCmd");
  if (cloneEl) {
    cloneEl.textContent = `git clone ${repo}.git\ncd telegram-sentiment-tracker`;
  }
  const contactEl = document.getElementById("gettoolContact");
  if (contactEl) {
    contactEl.innerHTML = appConfig.contactEmail
      ? `<a href="mailto:${appConfig.contactEmail}" style="color:var(--accent)">${appConfig.contactEmail}</a>`
      : "reach out via my resume site";
  }
  document.getElementById("portfolioBanner")?.classList.add("visible");
  document.getElementById("sidebarGithub")?.style.setProperty("display", "");
  for (const id of ["sidebarGithubLink", "bannerGithubLink"]) {
    const el = document.getElementById(id);
    if (el) {
      el.href = repo;
    }
  }
  const guideEl = document.getElementById("gettoolGuideLink");
  if (guideEl) {
    guideEl.href = `${repo.replace(/\/$/, "")}/blob/main/docs/GETTING_STARTED.md`;
  }
  document.getElementById("nav-messages")?.style.setProperty("display", "none");
  buildMobileNav();
}

function setDataBadge(kind) {
  const badge = document.getElementById("sheetStatusBadge");
  if (!badge) return;
  const map = {
    portfolio: ["Illustrative demo", "live"],
    sheet: ["Live", "live"],
    csv: ["Your data", "live"],
    demo: ["Demo", "demo"],
  };
  const [label, cls] = map[kind] || map.demo;
  badge.textContent = label;
  badge.className = `status-badge ${cls === "live" && kind === "portfolio" ? "live" : cls}`;
  if (kind === "portfolio") badge.className = "status-badge live";
}

function initNav() {
  document.querySelectorAll(".nav-item[data-nav]").forEach((el) => {
    el.addEventListener("click", () => navigate(el.dataset.nav));
  });
  document.querySelectorAll(".mode-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (btn.dataset.mode === "upload") navigate("upload");
      else navigate("dashboard");
    });
  });
  buildMobileNav();
}

// ── Parsing helpers ──────────────────────────────────────────────────
function normalizeHeaders(row) {
  const out = {};
  for (const [k, v] of Object.entries(row)) {
    out[k.replace(/^\ufeff/, "").trim().toLowerCase()] = v;
  }
  return out;
}

function parseSheetDate(val) {
  if (val == null || val === "") return new Date(NaN);
  const s = String(val).trim();
  const d = new Date(s);
  if (!isNaN(d.getTime())) return d;
  const n = parseFloat(s);
  if (!isNaN(n) && n > 30000 && n < 60000) {
    return new Date((n - 25569) * 86400 * 1000);
  }
  return new Date(NaN);
}

function pctOrZero(n, d) {
  return d ? Math.round((n / d) * 100) : 0;
}

function netScore(group) {
  const n = group.length || 1;
  const pos = group.filter((m) => m.sentiment_label === "pos").length;
  const neg = group.filter((m) => m.sentiment_label === "neg").length;
  return Math.round(((pos - neg) / n) * 100) / 100;
}

const DOMAIN_STOP = new Set([
  "stx", "btc", "eth", "sbtc", "strc", "usda", "usdc", "the", "and", "for",
  "스택스", "스택", "스택스는", "비트코인", "비트", "bitcoin", "stacks", "stack",
  "crypto", "크립토", "코인", "coin", "bitflow", "nakamoto", "pox", "sip", "tge",
]);

function isJunkKeyword(kw) {
  if (!kw || kw.length < 3) return true;
  if (/^[\W\d_.…?!,;:\s\-]+$/.test(kw)) return true;
  if (DOMAIN_STOP.has(kw.toLowerCase())) return true;
  if (/^[a-z]{2,4}$/i.test(kw)) return true;
  return false;
}

function cleanQuote(text) {
  return (text || "")
    .replace(/https?:\/\/\S+/g, "")
    .replace(/[\n\r]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function buildComplaintsForWeek(group) {
  const neg = group
    .filter((m) => m.sentiment_label === "neg")
    .map((m) => ({ ...m, quote: cleanQuote(m.text) }))
    .filter((m) => m.quote.length >= 12)
    .sort((a, b) => b.sentiment_score - a.sentiment_score);

  if (!neg.length) return [{ t: "(no negative messages this week)", n: 0, tEn: "", isQuote: true }];

  const seen = new Set();
  const quotes = [];
  for (const m of neg) {
    const key = m.quote.slice(0, 30).toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    const similar = neg.filter(
      (o) => o.quote.slice(0, 25).toLowerCase() === m.quote.slice(0, 25).toLowerCase()
    ).length;
    quotes.push({
      t: m.quote.slice(0, 100) + (m.quote.length > 100 ? "…" : ""),
      tEn: m.text_en || "",
      n: similar,
      isQuote: true,
    });
    if (quotes.length >= 5) break;
  }

  if (quotes.length) return quotes;

  const keywords = (group[0]?.top_complaints || "")
    .split("|")
    .map((s) => s.trim())
    .filter((s) => !isJunkKeyword(s))
    .slice(0, 5);

  return keywords.map((t) => ({
    t,
    tEn: "",
    n: neg.filter((m) => m.quote.toLowerCase().includes(t.toLowerCase())).length || 1,
    isQuote: false,
  }));
}

// ── Translation ──────────────────────────────────────────────────────
function hasKorean(text) {
  return /[가-힣]/.test(text || "");
}

function enCacheKey(text) {
  return `en:${text}`;
}

function getEnglish(text, bakedEn) {
  if (bakedEn) return bakedEn;
  return translationCache[enCacheKey(text)] || "";
}

async function translateTexts(texts) {
  const unique = [...new Set(texts.filter(Boolean))];
  const need = unique.filter((t) => hasKorean(t) && !translationCache[enCacheKey(t)]);
  if (!need.length) {
    return texts.map((t) => translationCache[enCacheKey(t)] || "");
  }

  try {
    const res = await fetch("/api/translate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ texts: need, target: "en", source: "ko" }),
    });
    if (!res.ok) {
      console.warn("Translation API error:", await res.text());
      return texts.map((t) => translationCache[enCacheKey(t)] || "");
    }
    const data = await res.json();
    need.forEach((t, i) => {
      const tr = data.translations[i] || "";
      if (tr) translationCache[enCacheKey(t)] = tr;
    });
    localStorage.setItem("st_translations_v2", JSON.stringify(translationCache));
  } catch (err) {
    console.warn("Translation fetch failed:", err);
  }
  return texts.map((t) => translationCache[enCacheKey(t)] || "");
}

function formatBilingual(koreanText, bakedEn) {
  const src = koreanText || "";
  if (lang === "ko") {
    return { main: src, sub: "" };
  }
  const en = getEnglish(src, bakedEn);
  if (en && hasKorean(src)) {
    return { main: en, sub: src };
  }
  return { main: en || src, sub: "" };
}

function collectTextsForTranslation() {
  const texts = [];
  recentMsgs.forEach((m) => texts.push(m.text));
  (complaints52[currentWeek] || []).forEach((c) => texts.push(c.t));
  posThemes.forEach((t) => texts.push(t.text));
  rawMessages.slice(0, 100).forEach((m) => texts.push(m.text));
  return texts.filter((t) => hasKorean(t));
}

function setAppLoading(on, message, sub) {
  const overlay = document.getElementById("appLoading");
  const msgEl = document.getElementById("appLoadingMsg");
  const subEl = document.getElementById("appLoadingSub");
  if (overlay) {
    overlay.classList.toggle("visible", on);
    overlay.setAttribute("aria-busy", on ? "true" : "false");
  }
  if (msgEl && message) msgEl.textContent = message;
  if (subEl && sub) subEl.textContent = sub;

  const badge = document.getElementById("sheetStatusBadge");
  const modeDesc = document.getElementById("modeDescText");
  if (on) {
    if (badge) {
      badge.textContent = "Loading";
      badge.className = "status-badge loading";
    }
    if (modeDesc && message) modeDesc.textContent = message;
  }
}

function ensureBootstrap() {
  if (!lineChart) initCharts();
}

function bootstrapApp() {
  currentWeek = weeks52.length - 1;
  ensureBootstrap();
  refreshUI();
  renderEventList();
}

function setTranslating(on, detail) {
  isTranslating = on;
  const message = detail || "Translating messages…";
  const html = on
    ? `<span class="lang-spinner" aria-hidden="true"></span><span>${message}</span>`
    : "";
  document.querySelectorAll(".lang-status").forEach((el) => {
    el.classList.toggle("visible", on);
    el.innerHTML = on ? html : "";
  });
  document.querySelectorAll(".lang-btn").forEach((btn) => {
    btn.disabled = on;
  });
  const msgNote = document.getElementById("msgNote");
  if (msgNote && on) msgNote.textContent = message;
}

function countTextsNeedingTranslation(texts) {
  const unique = [...new Set(texts.filter(Boolean))];
  return unique.filter((t) => hasKorean(t) && !translationCache[enCacheKey(t)]).length;
}


function parseAndApplyCsv(text) {
  const rows = Papa.parse(text, { header: true, skipEmptyLines: true }).data.map(normalizeHeaders);
  if (!rows.length) throw new Error("CSV is empty");
  applyMessageData(rows);
  if (!rawMessages.length) {
    throw new Error(
      "CSV loaded but 0 messages parsed. Ensure columns include msg_id, date, and sentiment_label."
    );
  }
  return rawMessages.length;
}

async function fetchAndApplyDemo() {
  showSheetStatus("Loading illustrative demo…", "loading");
  setAppLoading(true, "Loading community data…", "Fetching illustrative demo dataset");
  try {
    const res = await fetch("/api/demo");
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || res.statusText);
    }
    setAppLoading(true, "Loading community data…", "Parsing messages and building charts…");
    const count = parseAndApplyCsv(await res.text());
    dataSource = "portfolio";
    setDataBadge("portfolio");
    updateModeDesc("community");
    showSheetStatus(`Illustrative demo · ${count.toLocaleString()} synthetic messages loaded`, "ok");
    seedPortfolioEvents(true);
    navigate("dashboard");
  } finally {
    setAppLoading(false);
  }
}

async function handleCsvFile(file) {
  if (!file) return;
  const name = (file.name || "").toLowerCase();
  if (!name.endsWith(".csv")) {
    showSheetStatus("Please drop a CSV file from telegram_sentiment.py output.", "error");
    return;
  }
  setAppLoading(true, "Loading your CSV…", "Parsing in your browser — data stays local");
  try {
    const count = parseAndApplyCsv(await file.text());
    dataSource = "csv";
    setDataBadge("csv");
    updateModeDesc("community");
    showSheetStatus(`Loaded ${count.toLocaleString()} messages from ${file.name}`, "ok");
    navigate("dashboard");
  } catch (e) {
    showSheetStatus(`Could not load CSV: ${e.message}`, "error");
  } finally {
    setAppLoading(false);
  }
}

async function loadAppConfig() {
  try {
    const res = await fetch("/api/config");
    if (res.ok) appConfig = { ...appConfig, ...(await res.json()) };
  } catch {
    /* local dev without config endpoint */
  }
  embedMode = new URLSearchParams(window.location.search).get("embed") === "1";
  portfolioMode = appConfig.portfolioMode === true;
  if (portfolioMode || embedMode) applyPortfolioNav();
}

// ── Google Sheets ────────────────────────────────────────────────────
async function loadSheetFromInput() {
  const url = document.getElementById("sheetUrlInput").value.trim();
  if (!url) {
    showSheetStatus("Paste your Google Sheets URL first.", "error");
    return;
  }
  localStorage.setItem("st_sheet_url", url);
  setAppLoading(true, "Loading community data…", "Fetching from Google Sheets");
  try {
    await fetchAndApplySheet(url);
  } catch {
    /* status shown in fetchAndApplySheet */
  } finally {
    setAppLoading(false);
  }
}

async function fetchAndApplySheet(url) {
  showSheetStatus("Loading data from Google Sheets…", "loading");
  setAppLoading(true, "Loading community data…", "Fetching from Google Sheets");
  try {
    const res = await fetch(`/api/sheet?url=${encodeURIComponent(url)}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || res.statusText);
    }
    setAppLoading(true, "Loading community data…", "Parsing messages and building charts…");
    const count = parseAndApplyCsv(await res.text());

    dataSource = "sheet";
    setDataBadge("sheet");
    updateModeDesc("community");
    showSheetStatus(`Connected · ${count.toLocaleString()} messages parsed`, "ok");
    setMode("community", null, false);
    navigate("dashboard");
  } catch (e) {
    showSheetStatus(`Could not load sheet: ${e.message}`, "error");
    throw e;
  }
}

function showSheetStatus(msg, type) {
  const el = document.getElementById("sheetStatus");
  el.textContent = msg;
  el.className = `sheet-status ${type}`;
}

function applyMessageData(rows) {
  rawMessages = rows
    .map((r) => ({
      msg_id: r.msg_id,
      date: parseSheetDate(r.date),
      week_start: r.week_start || "",
      from: r.from || "unknown",
      from_id: r.from_id || "",
      text: r.text || "",
      text_en: r.text_en || "",
      sentiment_label: (r.sentiment_label || "neu").toLowerCase(),
      sentiment_score: parseFloat(r.sentiment_score) || 0.5,
      is_reply: String(r.is_reply).toUpperCase() === "TRUE",
      top_complaints: r.top_complaints || "",
      chat_name: r.chat_name || "Community",
    }))
    .filter((r) => !isNaN(r.date.getTime()));

  const agg = aggregateFromMessages(rawMessages);
  chartData = agg.chartData;
  chartKeys = agg.chartKeys;
  weeks52 = agg.weeks52;
  complaints52 = agg.complaints52;
  complainers = agg.complainers;
  responseData = agg.responseData;
  posThemes = agg.posThemes;
  recentMsgs = agg.recentMsgs;
  summary = agg.summary;
  currentWeek = Math.max(0, weeks52.length - 1);

  ensureBootstrap();
  refreshUI();
  buildWindowPills();
  applyChartView();
}

function aggregateFromMessages(msgs) {
  const valid = msgs.filter((m) => m.sentiment_label);
  const total = valid.length;
  const counts = { pos: 0, neg: 0, neu: 0 };
  valid.forEach((m) => counts[m.sentiment_label]++);

  const weekMap = new Map();
  valid.forEach((m) => {
    const w = m.week_start || m.date.toISOString().slice(0, 10);
    if (!weekMap.has(w)) weekMap.set(w, []);
    weekMap.get(w).push(m);
  });

  const weeks = [...weekMap.keys()].sort();
  const weeks52local = weeks.map((w) => {
    const d = new Date(w);
    return d.toLocaleDateString("en", { month: "short", day: "numeric", year: "numeric" });
  });

  const complaints52local = weeks.map((w) => buildComplaintsForWeek(weekMap.get(w)));

  const monthly = bucketByMonth(valid);
  const yearly = bucketByYear(valid);
  const weekly = bucketByWeek(valid, weeks);

  const negMsgs = valid.filter((m) => m.sentiment_label === "neg");
  const complainerMap = new Map();
  negMsgs.forEach((m) => {
    const key = m.from || m.from_id;
    complainerMap.set(key, (complainerMap.get(key) || 0) + 1);
  });
  const palette = [COLORS.neg, COLORS.neu, COLORS.net, COLORS.pos, COLORS.neg];
  const complainersLocal = [...complainerMap.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([name, n], i) => ({
      initials: name.slice(0, 2).toUpperCase(),
      color: palette[i],
      bg: COLORS.negBg,
      name,
      msgs: n,
      topics: "Most negative messages",
    }));

  const replies = valid.filter((m) => m.is_reply);
  const replyPos = replies.filter((m) => m.sentiment_label === "pos").length;
  const replyNeg = replies.filter((m) => m.sentiment_label === "neg").length;
  const replyTotal = replies.length || 1;

  const posMsgs = valid.filter((m) => m.sentiment_label === "pos");
  const themeWords = {};
  posMsgs.forEach((m) => {
    const label = positiveThemeLabel(m.text);
    themeWords[label] = (themeWords[label] || 0) + 1;
  });
  const posThemesLocal = Object.entries(themeWords)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([text, n]) => ({ text, textEn: "", n }));

  const recentMsgsLocal = [...valid]
    .sort((a, b) => b.date - a.date)
    .slice(0, 8)
    .map((m) => ({
      date: m.date.toLocaleDateString("en", { month: "short", day: "numeric" }),
      text: m.text.slice(0, 120),
      text_en: m.text_en || "",
      s: m.sentiment_label,
    }));

  const lastWeek = weeks.length ? weekMap.get(weeks[weeks.length - 1]) : [];
  const lwCounts = { pos: 0, neg: 0, neu: 0 };
  lastWeek.forEach((m) => lwCounts[m.sentiment_label]++);

  return {
    chartData: { monthly, weekly, yearly },
    chartKeys: {
      monthly: monthly.keys,
      weekly: weekly.keys,
      yearly: yearly.keys,
    },
    weeks52: weeks52local,
    complaints52: complaints52local,
    complainers: complainersLocal.length ? complainersLocal : demo.complainers,
    responseData: [
      {
        label: "Positive replies",
        sub: "Reply messages scored positive",
        color: "var(--pos)",
        badge: `${Math.round((replyPos / replyTotal) * 100)}%`,
        badgeBg: "var(--pos-bg)",
        badgeColor: "var(--pos)",
      },
      {
        label: "Negative replies",
        sub: "Reply messages scored negative",
        color: "var(--neg)",
        badge: `${Math.round((replyNeg / replyTotal) * 100)}%`,
        badgeBg: "var(--neg-bg)",
        badgeColor: "var(--neg)",
      },
      {
        label: "Other replies",
        sub: "Neutral or unscored replies",
        color: "var(--text3)",
        badge: `${Math.round(((replyTotal - replyPos - replyNeg) / replyTotal) * 100)}%`,
        badgeBg: "var(--card2)",
        badgeColor: "var(--text2)",
      },
    ],
    posThemes: posThemesLocal.length ? posThemesLocal : demo.posThemes,
    recentMsgs: recentMsgsLocal.length ? recentMsgsLocal : demo.recentMsgs,
    summary: {
      total,
      posPct: pctOrZero(counts.pos, total),
      negPct: pctOrZero(counts.neg, total),
      neuPct: pctOrZero(counts.neu, total),
      weekMsgs: lastWeek.length,
      weekPos: pctOrZero(lwCounts.pos, lastWeek.length),
      weekNeg: pctOrZero(lwCounts.neg, lastWeek.length),
      weekNeu: pctOrZero(lwCounts.neu, lastWeek.length),
    },
  };
}

function pctSentiment(group) {
  const n = group.length || 1;
  return {
    pos: Math.round((group.filter((m) => m.sentiment_label === "pos").length / n) * 100),
    neg: Math.round((group.filter((m) => m.sentiment_label === "neg").length / n) * 100),
    neu: Math.round((group.filter((m) => m.sentiment_label === "neu").length / n) * 100),
  };
}

function bucketData(map, keys, labelFn) {
  const labels = keys.map(labelFn);
  const pos = [], neg = [], neu = [], net = [];
  keys.forEach((k) => {
    const group = map.get(k) || [];
    const p = pctSentiment(group);
    pos.push(p.pos);
    neg.push(p.neg);
    neu.push(p.neu);
    net.push(netScore(group));
  });
  return { labels, keys, pos, neg, neu, net };
}

function positiveThemeLabel(text) {
  const rules = [
    [/메인넷|mainnet|업그레이드|upgrade|patch|rollout|블록/i, "Mainnet upgrades"],
    [/스테이킹|staking|리워드|reward|epoch|APY|delegat|unbond/i, "Staking rewards"],
    [/커뮤니티|community|답변|helpful|모더|member|workaround/i, "Community support"],
    [/거버넌스|governance|AMA|로드맵|roadmap|HIP|투표|vote/i, "Governance & AMA"],
    [/테스트넷|testnet|faucet|sandbox|샌드박스/i, "Testnet stability"],
    [/온보딩|onboarding|가이드|docs|문서|FAQ|tutorial/i, "Onboarding & docs"],
    [/노드|validator|밸리|검증|monitoring|slot/i, "Validator operations"],
    [/지갑|wallet|연동|connect/i, "Wallet experience"],
  ];
  for (const [re, label] of rules) {
    if (re.test(text || "")) return label;
  }
  return "General praise";
}

function bucketByMonth(msgs) {
  const map = new Map();
  msgs.forEach((m) => {
    const key = `${m.date.getFullYear()}-${String(m.date.getMonth() + 1).padStart(2, "0")}`;
    if (!map.has(key)) map.set(key, []);
    map.get(key).push(m);
  });
  const keys = [...map.keys()].sort();
  return bucketData(map, keys, (k) => {
    const [y, mo] = k.split("-");
    const d = new Date(y, mo - 1);
    return d.toLocaleString("en", { month: "short", year: "numeric" });
  });
}

function bucketByYear(msgs) {
  const map = new Map();
  msgs.forEach((m) => {
    const y = String(m.date.getFullYear());
    if (!map.has(y)) map.set(y, []);
    map.get(y).push(m);
  });
  const keys = [...map.keys()].sort();
  return bucketData(map, keys, (k) => k);
}

function bucketByWeek(msgs, weeks) {
  const map = new Map();
  msgs.forEach((m) => {
    const w = m.week_start || m.date.toISOString().slice(0, 10);
    if (!map.has(w)) map.set(w, []);
    map.get(w).push(m);
  });
  return bucketData(map, weeks, (w) => {
    const d = new Date(w);
    return d.toLocaleString("en", { month: "short", day: "numeric", year: "numeric" });
  });
}

// ── Charts ───────────────────────────────────────────────────────────
function sliceChartBucket(d, n) {
  if (!d || n === Infinity || d.labels.length <= n) return d;
  const start = d.labels.length - n;
  const slice = (arr) => arr.slice(start);
  return {
    labels: slice(d.labels),
    keys: slice(d.keys),
    pos: slice(d.pos),
    neg: slice(d.neg),
    neu: slice(d.neu),
    net: slice(d.net),
  };
}

function getWindowN(range) {
  const id = currentWindow[range];
  const opt = CHART_WINDOWS[range].find((w) => w.id === id);
  return opt ? opt.n : Infinity;
}

function getChartView(range) {
  const full = chartData[range];
  if (!full) return full;
  return sliceChartBucket(full, getWindowN(range));
}

function buildWindowPills() {
  const wrap = document.getElementById("windowPills");
  if (!wrap) return;
  const options = CHART_WINDOWS[currentRange];
  wrap.innerHTML = options
    .map(
      (w) =>
        `<button type="button" class="wpill${currentWindow[currentRange] === w.id ? " active" : ""}" data-window="${w.id}">${w.label}</button>`
    )
    .join("");
  wrap.querySelectorAll(".wpill").forEach((btn) => {
    btn.addEventListener("click", () => {
      currentWindow[currentRange] = btn.dataset.window;
      buildWindowPills();
      applyChartView();
    });
  });
}

function applyChartView() {
  const d = getChartView(currentRange);
  const winLabel = CHART_WINDOWS[currentRange].find((w) => w.id === currentWindow[currentRange])?.label || "";
  const subs = {
    weekly: `Weekly · ${winLabel} · hover for detail`,
    monthly: `Monthly · ${winLabel} · hover for detail`,
    yearly: `Yearly · ${winLabel} · hover for detail`,
  };
  document.getElementById("chartSub").textContent = subs[currentRange];
  if (!lineChart || !d) return;
  lineChart.data.labels = d.labels;
  lineChart.data.datasets[0].data = d.pos;
  lineChart.data.datasets[1].data = d.neg;
  lineChart.data.datasets[2].data = d.neu;
  lineChart.data.datasets[3].data = d.net;
  lineChart.options.scales.x.ticks.maxTicksLimit = d.labels.length > 40 ? 14 : 18;
  lineChart.update();
  updateLegendUI();
  setTimeout(renderAnnotations, 100);
}

function initCharts() {
  buildWindowPills();
  const initial = getChartView(currentRange);
  lineChart = new Chart(document.getElementById("lineChart"), {
    type: "line",
    data: {
      labels: initial.labels,
      datasets: [
        ds("Positive", initial.pos, COLORS.pos, COLORS.posBg, "y", 1.5),
        ds("Negative", initial.neg, COLORS.neg, COLORS.negBg, "y", 1.5),
        ds("Neutral", initial.neu, COLORS.neu, COLORS.neuBg, "y", 1.5, [4, 4]),
        ds("Net sentiment", initial.net, COLORS.net, "transparent", "yNet", 2, [6, 3], false),
      ],
    },
    options: chartOptions(),
  });
  initChartLegend();
  applyChartView();
}

function ds(label, data, color, bg, yAxisID, width, dash, fill = true) {
  return {
    label,
    data,
    yAxisID,
    borderColor: color,
    backgroundColor: bg,
    tension: 0.35,
    fill,
    pointRadius: 2,
    pointHoverRadius: 5,
    pointBackgroundColor: color,
    pointBorderColor: "#0F0F12",
    pointBorderWidth: 1,
    borderWidth: width,
    borderDash: dash || [],
  };
}

function chartOptions() {
  return {
    responsive: true,
    animation: { duration: 400, onComplete: () => renderAnnotations() },
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: "#1A1A1D",
        titleColor: "#FFFFFF",
        bodyColor: "#8E8E93",
        borderColor: "#2C2C2E",
        borderWidth: 1,
        padding: 10,
        cornerRadius: 8,
        callbacks: {
          afterBody(items) {
            const netItem = items.find((i) => i.datasetIndex === SERIES_INDEX.net);
            if (netItem) {
              const v = netItem.raw;
              return `Net: ${v > 0 ? "+" : ""}${v}`;
            }
            return "";
          },
        },
      },
    },
    scales: {
      x: {
        grid: { color: "rgba(255,255,255,.03)" },
        ticks: {
          color: "#8E8E93",
          font: { family: "Inter", size: 10 },
          maxRotation: 45,
          autoSkip: true,
          maxTicksLimit: 18,
        },
      },
      y: {
        position: "left",
        grid: { color: "rgba(255,255,255,.03)" },
        ticks: {
          color: "#8E8E93",
          font: { family: "Inter", size: 10 },
          callback: (v) => v + "%",
        },
        min: 0,
        max: 85,
      },
      yNet: {
        position: "right",
        grid: { drawOnChartArea: false },
        ticks: {
          color: COLORS.net,
          font: { family: "Inter", size: 10 },
          callback: (v) => (v > 0 ? "+" : "") + v.toFixed(1),
        },
        min: -1,
        max: 1,
      },
    },
  };
}

function initChartLegend() {
  document.querySelectorAll(".leg[data-series]").forEach((el) => {
    el.addEventListener("click", () => toggleSeries(el.dataset.series));
  });
}

function toggleSeries(name) {
  if (!lineChart) return;
  const idx = SERIES_INDEX[name];
  const visible = lineChart.isDatasetVisible(idx);
  lineChart.setDatasetVisibility(idx, !visible);
  if (name === "net") {
    lineChart.options.scales.yNet.display = !visible;
  }
  lineChart.update();
  updateLegendUI();
}

function updateLegendUI() {
  if (!lineChart) return;
  document.querySelectorAll(".leg[data-series]").forEach((el) => {
    const idx = SERIES_INDEX[el.dataset.series];
    const visible = lineChart.isDatasetVisible(idx);
    el.classList.toggle("off", !visible);
    el.classList.toggle("on", visible);
    el.setAttribute("aria-pressed", visible ? "true" : "false");
  });
}

function updateChartRange(r, btn) {
  currentRange = r;
  if (btn) {
    document.querySelectorAll(".rpill").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
  }
  buildWindowPills();
  applyChartView();
}

function parseEventTime(date) {
  if (!date) return NaN;
  if (date.length >= 10) return new Date(date.slice(0, 10)).getTime();
  if (date.length === 7) return new Date(`${date}-01`).getTime();
  if (date.length === 4) return new Date(`${date}-06-01`).getTime();
  return NaN;
}

function keyRangeStart(key, range) {
  if (range === "yearly") return new Date(`${key}-01-01`).getTime();
  if (range === "monthly") return new Date(`${key}-01`).getTime();
  return new Date(String(key).slice(0, 10)).getTime();
}

function keyRangeEnd(key, range) {
  if (range === "yearly") return new Date(`${key}-12-31T23:59:59`).getTime();
  if (range === "monthly") {
    const [y, m] = key.split("-").map(Number);
    return new Date(y, m, 0, 23, 59, 59).getTime();
  }
  const d = new Date(String(key).slice(0, 10));
  d.setDate(d.getDate() + 6);
  d.setHours(23, 59, 59, 999);
  return d.getTime();
}

function eventInVisibleRange(ev, keys, range) {
  const evTime = parseEventTime(ev.date);
  if (Number.isNaN(evTime)) return false;
  const start = keyRangeStart(keys[0], range);
  const end = keyRangeEnd(keys[keys.length - 1], range);
  return evTime >= start && evTime <= end;
}

function nearestKeyIndex(targetTime, keys, range) {
  let best = -1;
  let bestDist = Infinity;
  keys.forEach((k, i) => {
    const kt = keyRangeStart(k, range);
    const dist = Math.abs(kt - targetTime);
    if (dist < bestDist) {
      bestDist = dist;
      best = i;
    }
  });
  return best;
}

function eventChartIndex(ev, keys, range) {
  if (!keys.length) return -1;
  if (!eventInVisibleRange(ev, keys, range)) return -1;

  const date = ev.date || "";
  if (range === "yearly") {
    const y = date.slice(0, 4);
    const idx = keys.indexOf(y);
    return idx >= 0 ? idx : nearestKeyIndex(parseEventTime(date), keys, range);
  }
  if (range === "monthly") {
    const monthKey = date.length >= 7 ? date.slice(0, 7) : date;
    const idx = keys.indexOf(monthKey);
    return idx >= 0 ? idx : nearestKeyIndex(parseEventTime(date), keys, range);
  }
  if (range === "weekly") {
    const iso = date.length >= 10 ? date.slice(0, 10) : `${date.slice(0, 7)}-15`;
    const idx = keys.indexOf(iso);
    if (idx >= 0) return idx;
    return nearestKeyIndex(new Date(iso).getTime(), keys, range);
  }
  return -1;
}

function renderAnnotations() {
  const wrap = document.getElementById("chartAnnotations");
  wrap.innerHTML = "";
  if (!lineChart?.chartArea) return;
  const { chartArea } = lineChart;
  const view = getChartView(currentRange);
  const keys = view?.keys || chartKeys[currentRange] || [];
  const n = keys.length;
  if (n < 2) return;
  const stepW = (chartArea.right - chartArea.left) / (n - 1);

  const plotted = events
    .map((ev) => ({ ev, idx: eventChartIndex(ev, keys, currentRange) }))
    .filter(({ idx }) => idx >= 0 && idx < n)
    .sort((a, b) => a.idx - b.idx || a.ev.id - b.ev.id);

  plotted.forEach(({ ev, idx }) => {
    const cfg = typeConfig[ev.type] || typeConfig.acc;
    let x = chartArea.left + idx * stepW;
    let y = chartArea.top + 20;

    const netMeta = lineChart.getDatasetMeta(SERIES_INDEX.net);
    const pt = netMeta?.data?.[idx];
    const netVal = view?.net?.[idx];
    if (pt && lineChart.isDatasetVisible(SERIES_INDEX.net)) {
      x = pt.x;
      y = pt.y;
    } else if (netVal != null && lineChart.scales.yNet) {
      y = lineChart.scales.yNet.getPixelForValue(netVal);
    }

    const guide = document.createElement("div");
    guide.className = "chart-event-guide";
    guide.style.cssText = `left:${x}px;top:${chartArea.top}px;height:${chartArea.bottom - chartArea.top}px;border-color:${cfg.color}`;
    wrap.appendChild(guide);

    const overlap = plotted.filter((p) => p.idx === idx);
    const slot = overlap.findIndex((p) => p.ev.id === ev.id);
    const labelTop = chartArea.top + 4 + slot * 22;

    const label = document.createElement("div");
    label.className = "chart-milestone-label";
    label.textContent = ev.label;
    label.title = ev.label;
    label.style.cssText = `left:${x}px;top:${labelTop}px;color:${cfg.color};border-color:${cfg.color}`;

    const labelBottom = labelTop + 20;
    const stemHeight = Math.max(0, y - labelBottom - 6);
    if (stemHeight > 2) {
      const stem = document.createElement("div");
      stem.className = "chart-milestone-stem";
      stem.style.cssText = `left:${x}px;top:${labelBottom}px;height:${stemHeight}px;border-color:${cfg.color}`;
      wrap.appendChild(stem);
    }

    const pin = document.createElement("div");
    pin.className = "chart-milestone-pin";
    pin.style.cssText = `left:${x}px;top:${y}px;background:${cfg.color}`;

    wrap.appendChild(label);
    wrap.appendChild(pin);
  });
}

// ── UI render ────────────────────────────────────────────────────────
function refreshUI() {
  document.getElementById("sumTotal").textContent = summary.total.toLocaleString();
  document.getElementById("sumPos").textContent = summary.posPct + "%";
  document.getElementById("sumNeg").textContent = summary.negPct + "%";
  document.getElementById("sumNeu").textContent = summary.neuPct + "%";
  document.getElementById("weekMsgCount").textContent = summary.weekMsgs + " msgs";
  document.getElementById("barPos").style.width = summary.weekPos + "%";
  document.getElementById("barNeg").style.width = summary.weekNeg + "%";
  document.getElementById("barNeu").style.width = summary.weekNeu + "%";
  document.getElementById("pctPos").textContent = summary.weekPos + "%";
  document.getElementById("pctNeg").textContent = summary.weekNeg + "%";
  document.getElementById("pctNeu").textContent = summary.weekNeu + "%";
  document.getElementById("complaintBadge").textContent = complaints52[currentWeek]?.length || 0;

  buildDropdown();
  renderComplaints();
  renderComplainers();
  renderResponseSentiment();
  renderPositiveThemes();
  renderMsgs().catch(() => {});
  runMessageSearch().catch(() => {});
}

function buildDropdown() {
  const sel = document.getElementById("weekSelect");
  sel.innerHTML = weeks52
    .map((w, i) => `<option value="${i}"${i === currentWeek ? " selected" : ""}>${w}</option>`)
    .join("");
}

function setWeek(i) {
  currentWeek = parseInt(i, 10);
  renderComplaints();
}

function complaintHtml(c, j, max) {
  const { main: label, sub: subText } = formatBilingual(c.t, c.tEn);
  const sub = subText ? `<div class="c-sub">${subText}</div>` : "";
  const countLabel = c.isQuote ? (c.n > 1 ? `${c.n} similar` : "1 msg") : `${c.n} msgs`;
  return `<div class="complaint"><span class="c-rank">${j + 1}</span><div class="c-text-wrap"><span class="c-text${c.isQuote ? " c-quote" : ""}">${label}</span>${sub}</div>
    <div class="c-bar-wrap"><div class="c-bar-bg"><div class="c-bar" style="width:${Math.round((c.n / max) * 100)}%"></div></div><div class="c-count">${countLabel}</div></div></div>`;
}

async function renderComplaints() {
  const d = complaints52[currentWeek] || [];
  const max = d[0]?.n || 1;
  if (lang === "en") {
    const translated = await translateTexts(d.map((c) => c.t));
    d.forEach((c, i) => { c.tEn = translated[i] || c.tEn; });
  }
  document.getElementById("complaintList").innerHTML = d.map((c, j) => complaintHtml(c, j, max)).join("");
}

function complainersAreProtected() {
  // Synthetic portfolio demo uses fictional names — no lock needed
  if (portfolioMode || dataSource === "portfolio") return false;
  return dataSource !== "demo";
}

function complainersUnlocked() {
  return sessionStorage.getItem(COMPLAINERS_UNLOCK_KEY) === "1";
}

let complainerUnlockOpen = false;

function showComplainerUnlockForm() {
  complainerUnlockOpen = true;
  renderComplainers();
  setTimeout(() => document.getElementById("complainerPw")?.focus(), 0);
}

function unlockComplainers() {
  const input = document.getElementById("complainerPw");
  const err = document.getElementById("complainerPwErr");
  if (!input) return;
  if (input.value === COMPLAINERS_DEMO_PW) {
    sessionStorage.setItem(COMPLAINERS_UNLOCK_KEY, "1");
    complainerUnlockOpen = false;
    if (err) err.textContent = "";
    renderComplainers();
  } else if (err) {
    err.textContent = "Incorrect password";
  }
}

function renderComplainers() {
  const el = document.getElementById("complainerList");
  if (!el) return;

  if (complainersAreProtected() && !complainersUnlocked()) {
    const totalMsgs = complainers.reduce((s, c) => s + (c.msgs || 0), 0);
    const unlockUi = complainerUnlockOpen
      ? `<div class="complainer-lock-row">
          <input type="password" class="form-input complainer-pw" id="complainerPw" placeholder="Password" autocomplete="off"
            onkeydown="if(event.key==='Enter')unlockComplainers()">
          <button type="button" class="btn-save" onclick="unlockComplainers()">Unlock</button>
        </div>
        <div class="complainer-pw-err" id="complainerPwErr"></div>`
      : `<button type="button" class="btn-secondary complainer-unlock-btn" onclick="showComplainerUnlockForm()">View member names</button>`;

    el.innerHTML = `
      <div class="complainer-lock">
        <div class="complainer-lock-sub">${complainers.length} active voices · ${totalMsgs.toLocaleString()} negative msgs</div>
        ${unlockUi}
      </div>
      ${complainers
        .map(
          (c, i) => `
      <div class="complainer-row complainer-row-masked">
        <div class="complainer-avatar" style="background:var(--card2);color:var(--text3)">?</div>
        <div style="flex:1;min-width:0"><div class="complainer-name">Member ${i + 1}</div><div class="complainer-sub">Hidden until unlocked</div></div>
        <div style="text-align:right"><div class="complainer-msgs">${c.msgs}</div><div class="complainer-label">msgs</div></div>
      </div>`
        )
        .join("")}`;
    return;
  }

  complainerUnlockOpen = false;

  el.innerHTML = complainers
    .map(
      (c) => `
    <div class="complainer-row"><div class="complainer-avatar" style="background:${c.bg};color:${c.color}">${c.initials}</div>
    <div style="flex:1;min-width:0"><div class="complainer-name">${c.name}</div><div class="complainer-sub">${c.topics}</div></div>
    <div style="text-align:right"><div class="complainer-msgs">${c.msgs}</div><div class="complainer-label">msgs</div></div></div>`
    )
    .join("");
}

function renderResponseSentiment() {
  document.getElementById("responseSentiment").innerHTML = responseData
    .map(
      (r) => `
    <div class="resp-row"><div class="resp-dot" style="background:${r.color}"></div>
    <div style="flex:1"><div class="resp-label">${r.label}</div><div class="resp-sub">${r.sub}</div></div>
    <div class="resp-badge" style="background:${r.badgeBg};color:${r.badgeColor}">${r.badge}</div></div>`
    )
    .join("");
}

async function renderPositiveThemes() {
  const max = posThemes[0]?.n || 1;
  if (lang === "en") {
    const translated = await translateTexts(posThemes.map((t) => t.text));
    posThemes.forEach((t, i) => { t.textEn = translated[i] || t.textEn; });
  }
  document.getElementById("positiveThemes").innerHTML = posThemes
    .map((t) => {
      const { main: label, sub: subText } = formatBilingual(t.text, t.textEn);
      const sub = subText ? `<div class="theme-sub">${subText}</div>` : "";
      return `<div class="theme-row"><div class="theme-text-wrap"><div class="theme-text">${label}</div>${sub}</div>
    <div class="theme-bar-wrap"><div class="theme-bar-bg"><div class="theme-bar" style="width:${Math.round((t.n / max) * 100)}%"></div></div><div class="theme-count">${t.n} msgs</div></div></div>`;
    })
    .join("");
}

async function renderMsgs() {
  if (lang === "en" && !isTranslating) {
    await translateTexts(recentMsgs.map((m) => m.text));
    document.getElementById("msgNote").textContent = "English + Korean original below";
  } else if (lang === "ko") {
    document.getElementById("msgNote").textContent = "Korean chat";
  }
  document.getElementById("msgFeed").innerHTML = recentMsgs
    .map((m) => {
      const { main, sub: subText } = formatBilingual(m.text, m.text_en);
      const sub = subText ? `<div class="msg-sub">${subText}</div>` : "";
      return `<div class="msg"><div class="msg-top"><span class="msg-date">${m.date}</span><span class="spill s-${m.s}">${m.s.toUpperCase()}</span></div>
    <div class="msg-text">${main}</div>${sub}</div>`;
    })
    .join("");
}

let isMsgSearchRunning = false;

function formatMessageAuthor(m) {
  const name = (m.from || "").trim();
  if (name && name !== "unknown") return name;
  const id = (m.from_id || "").trim();
  if (id) return id;
  return "no id";
}

function setMsgSearchStatus(on, message) {
  const el = document.getElementById("msgSearchStatus");
  const btn = document.getElementById("msgSearchBtn");
  if (!el) return;
  if (on) {
    el.className = "msg-search-status loading";
    el.innerHTML = `<span class="msg-search-spinner" aria-hidden="true"></span><span>${message || "Searching…"}</span>`;
    if (btn) btn.disabled = true;
  } else {
    el.className = "msg-search-status";
    el.innerHTML = message ? `<span>${message}</span>` : "";
    if (btn) btn.disabled = false;
  }
}

async function runMessageSearch() {
  if (isMsgSearchRunning) return;
  isMsgSearchRunning = true;
  setMsgSearchStatus(true, "Searching messages…");
  try {
    await renderMessageTable();
  } finally {
    isMsgSearchRunning = false;
  }
}

async function renderMessageTable() {
  const q = (document.getElementById("msgSearch")?.value || "").toLowerCase().trim();
  const el = document.getElementById("msgTable");
  if (!el) return;

  if (!rawMessages.length) {
    setMsgSearchStatus(false, "");
    el.innerHTML = `<div style="color:var(--text3);font-size:12px;padding:20px 0">Connect Google Sheets or run analysis to see messages here.</div>`;
    return;
  }

  const sorted = [...rawMessages].sort((a, b) => b.date - a.date);
  const filtered = sorted.filter(
    (m) => !q || m.text.toLowerCase().includes(q) || (m.text_en || "").toLowerCase().includes(q)
  );
  const rows = filtered.slice(0, 200);
  const meta = document.getElementById("msgLogMeta");
  if (meta) {
    meta.textContent = q
      ? `${filtered.length.toLocaleString()} match${filtered.length === 1 ? "" : "es"} · newest first`
      : "Newest first";
  }

  if (!rows.length) {
    setMsgSearchStatus(false, q ? `No messages match “${q.slice(0, 40)}${q.length > 40 ? "…" : ""}”` : "");
    el.innerHTML = `<div style="color:var(--text3);font-size:12px;padding:20px 0">No messages match your search.</div>`;
    return;
  }

  if (lang === "en") {
    setMsgSearchStatus(true, `Translating ${rows.length} message${rows.length === 1 ? "" : "s"}…`);
    await translateTexts(rows.map((m) => m.text));
  }

  el.innerHTML = rows
    .map((m) => {
      const { main, sub: subText } = formatBilingual(m.text, m.text_en);
      const sub = subText ? `<div class="msg-sub">${subText.slice(0, 200)}</div>` : "";
      const author = formatMessageAuthor(m);
      return `<div class="msg"><div class="msg-top"><span class="msg-date">${m.date.toLocaleDateString()}</span><span class="spill s-${m.sentiment_label}">${m.sentiment_label.toUpperCase()}</span></div>
    <div class="msg-text"><strong>${author}</strong> · ${main.slice(0, 200)}</div>${sub}</div>`;
    })
    .join("");

  const status = q
    ? `Showing ${rows.length} of ${filtered.length.toLocaleString()} matches (newest first)`
    : `Showing ${rows.length} most recent of ${rawMessages.length.toLocaleString()} messages`;
  setMsgSearchStatus(false, status);
}

// ── Events ───────────────────────────────────────────────────────────
function toggleForm() {
  document.getElementById("addEventForm").classList.toggle("open");
}

function saveEvent() {
  const date = document.getElementById("eventDate").value;
  const label = document.getElementById("eventLabel").value.trim();
  const type = document.getElementById("eventType").value;
  if (!date || !label) return;
  events.push({ id: nextId++, date, label, type });
  localStorage.setItem("st_events", JSON.stringify(events));
  document.getElementById("addEventForm").classList.remove("open");
  renderEventList();
  renderAnnotations();
}

function deleteEvent(id) {
  events = events.filter((e) => e.id !== id);
  localStorage.setItem("st_events", JSON.stringify(events));
  renderEventList();
  renderAnnotations();
}

function renderEventList() {
  document.getElementById("eventCount").textContent = `(${events.length} event${events.length !== 1 ? "s" : ""})`;
  document.getElementById("eventList").innerHTML = events
    .map((ev) => {
      const cfg = typeConfig[ev.type] || typeConfig.acc;
      const displayDate =
        ev.date.length === 7
          ? new Date(ev.date + "-01").toLocaleString("en", { month: "short", year: "numeric" })
          : new Date(ev.date).toLocaleString("en", { month: "short", day: "numeric", year: "numeric" });
      return `<div class="event-item">
      <div class="event-marker" style="background:${cfg.color}"></div>
      <div class="event-date">${displayDate}</div>
      <div class="event-label">${ev.label}</div>
      <div class="event-type-badge" style="background:${cfg.bg};color:${cfg.color}">${cfg.label}</div>
      <button class="event-delete" onclick="deleteEvent(${ev.id})">×</button>
    </div>`;
    })
    .join("");
}

async function setLang(l) {
  if (isTranslating) return;
  lang = l;
  document.querySelectorAll(".lang-btn").forEach((btn) => {
    const isKo = btn.id === "lko" || btn.textContent.trim() === "한국어";
    btn.classList.toggle("active", l === "ko" ? isKo : !isKo);
  });
  try {
    if (l === "en") {
      const texts = collectTextsForTranslation();
      const need = countTextsNeedingTranslation(texts);
      if (need > 0) {
        setTranslating(true, `Translating ${need.toLocaleString()} message${need === 1 ? "" : "s"}…`);
      } else {
        setTranslating(true, "Applying English view…");
      }
      await translateTexts(texts);
    }
    await renderMsgs();
    await runMessageSearch();
    await renderComplaints();
    await renderPositiveThemes();
  } finally {
    setTranslating(false);
  }
}

function handleFile(f) {
  if (!f) return;
  document.getElementById("dropZone").innerHTML = `
    <div class="upload-icon">↑</div>
    <div style="font-size:14px;font-weight:600;margin-bottom:5px">${f.name} selected</div>
    <div style="font-size:12px;color:var(--text2);max-width:400px;margin:0 auto;line-height:1.6">
      To analyze this export, run the Python tool on your computer.<br><br>
      <code style="background:var(--card2);padding:4px 8px;border-radius:4px;font-size:11px">python telegram_sentiment.py -i "${f.name}" --lang ${lang}</code>
    </div>`;
}

function useDemoData() {
  dataSource = "demo";
  chartData = { ...demo.chartData };
  chartKeys = { ...demo.chartKeys };
  weeks52 = [...demo.weeks52];
  complaints52 = [...demo.complaints52];
  complainers = [...demo.complainers];
  responseData = [...demo.responseData];
  posThemes = [...demo.posThemes];
  recentMsgs = [...demo.recentMsgs];
  summary = { ...demo.summary };
  rawMessages = [];
  currentWeek = weeks52.length - 1;
  setDataBadge("demo");
  updateModeDesc("community");
  ensureBootstrap();
  refreshUI();
  buildWindowPills();
  applyChartView();
  showSheetStatus("Offline chart preview · run server for full 135k synthetic dataset.", "ok");
  navigate("dashboard");
}

// ── Init ─────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  initNav();

  document.querySelectorAll(".rpill").forEach((btn) => {
    btn.addEventListener("click", () => updateChartRange(btn.dataset.range, btn));
  });
  document.getElementById("weekSelect").addEventListener("change", (e) => setWeek(e.target.value));
  document.getElementById("lko").addEventListener("click", () => setLang("ko"));
  document.getElementById("len").addEventListener("click", () => setLang("en"));
  document.getElementById("connectSheetBtn").addEventListener("click", loadSheetFromInput);
  document.getElementById("useDemoBtn").addEventListener("click", async () => {
    setAppLoading(true, "Loading illustrative demo…", "Fetching synthetic dataset");
    try {
      await fetchAndApplyDemo();
    } catch {
      useDemoData();
    } finally {
      setAppLoading(false);
    }
  });
  document.getElementById("msgSearchBtn")?.addEventListener("click", () => runMessageSearch());
  document.getElementById("msgSearch")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      runMessageSearch();
    }
  });

  const csvDrop = document.getElementById("csvDropZone");
  if (csvDrop) {
    csvDrop.addEventListener("dragover", (e) => e.preventDefault());
    csvDrop.addEventListener("drop", (e) => {
      e.preventDefault();
      handleCsvFile(e.dataTransfer.files[0]);
    });
  }
  document.getElementById("csvFileInput")?.addEventListener("change", (e) => handleCsvFile(e.target.files[0]));

  const drop = document.getElementById("dropZone");
  if (drop) {
    drop.addEventListener("dragover", (e) => e.preventDefault());
    drop.addEventListener("drop", (e) => {
      e.preventDefault();
      handleFile(e.dataTransfer.files[0]);
    });
  }
  document.getElementById("fileInput")?.addEventListener("change", (e) => handleFile(e.target.files[0]));

  window.addEventListener("resize", () => {
    clearTimeout(window._rt);
    window._rt = setTimeout(renderAnnotations, 150);
  });

  initApp();
});

async function initApp() {
  await loadAppConfig();

  if (portfolioMode) {
    seedPortfolioEvents(true);
    setAppLoading(true, "Loading community data…", "Fetching illustrative demo dataset");
    try {
      await fetchAndApplyDemo();
    } catch (e) {
      console.warn("Portfolio demo load failed:", e);
      useDemoData();
    } finally {
      setAppLoading(false);
    }
    applyInitialPanel();
    return;
  }

  const saved = localStorage.getItem("st_sheet_url");
  if (saved) {
    document.getElementById("sheetUrlInput").value = saved;
    setAppLoading(true, "Loading community data…", "Fetching from Google Sheets");
    try {
      await fetchAndApplySheet(saved);
    } catch {
      useDemoData();
    } finally {
      setAppLoading(false);
    }
  } else {
    setAppLoading(true, "Loading community data…", "Fetching illustrative demo dataset");
    try {
      await fetchAndApplyDemo();
    } catch {
      useDemoData();
    } finally {
      setAppLoading(false);
    }
  }
  applyInitialPanel();
}

window.navigate = navigate;
window.toggleForm = toggleForm;
window.saveEvent = saveEvent;
window.deleteEvent = deleteEvent;
window.setLang = setLang;
window.handleFile = handleFile;
window.handleCsvFile = handleCsvFile;
window.unlockComplainers = unlockComplainers;
window.showComplainerUnlockForm = showComplainerUnlockForm;
window.setWeek = setWeek;
window.refreshUI = refreshUI;
window.renderComplaints = renderComplaints;
window.translateTexts = translateTexts;
window.getComplaints52 = () => complaints52;
window.getCurrentWeek = () => currentWeek;
window.getLang = () => lang;
