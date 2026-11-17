"use strict";

// ====================== Chhote helpers ======================
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const SVG_NS = "http://www.w3.org/2000/svg";

function make(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = text;
  return node;
}

function svgEl(name, attrs, parent) {
  const node = document.createElementNS(SVG_NS, name);
  for (const [key, value] of Object.entries(attrs || {})) node.setAttribute(key, value);
  if (parent) parent.appendChild(node);
  return node;
}

// Icons: sirf yahan likhe hue (bharose wale) SVG paths. User ka text kabhi innerHTML mein nahi jata.
const ICON_PATHS = {
  sparkle: '<path d="M12 3.5l1.55 4.45a2 2 0 0 0 1.25 1.25L19.25 10.75l-4.45 1.55a2 2 0 0 0-1.25 1.25L12 18l-1.55-4.45a2 2 0 0 0-1.25-1.25L4.75 10.75 9.2 9.2a2 2 0 0 0 1.25-1.25z"/><path d="M18.5 16.5l.5 1.5 1.5.5-1.5.5-.5 1.5-.5-1.5-1.5-.5 1.5-.5z"/>',
  chat: '<path d="M20 11.75a7.75 7.75 0 0 1-11.3 6.9L4.5 19.75l1.1-4A7.75 7.75 0 1 1 20 11.75z"/>',
  layers: '<path d="M12 4l8.5 4.25L12 12.5 3.5 8.25z"/><path d="M3.5 12.25L12 16.5l8.5-4.25"/><path d="M3.5 16.25L12 20.5l8.5-4.25"/>',
  database: '<path d="M12 4l8.5 4.25L12 12.5 3.5 8.25z"/><path d="M3.5 12.25L12 16.5l8.5-4.25"/><path d="M3.5 16.25L12 20.5l8.5-4.25"/>',
  book: '<path d="M12 6.5C10.5 5.2 8.3 4.5 4.5 4.5v13c3.8 0 6 .7 7.5 2 1.5-1.3 3.7-2 7.5-2v-13c-3.8 0-6 .7-7.5 2z"/><path d="M12 6.5v13"/>',
  chart: '<path d="M4 19.5h16"/><path d="M7.5 16v-4.5"/><path d="M12 16V7.5"/><path d="M16.5 16v-6"/>',
  search: '<circle cx="11" cy="11" r="6.25"/><path d="M19.5 19.5l-4-4"/>',
  mic: '<rect x="9" y="3.75" width="6" height="10.5" rx="3"/><path d="M5.75 11.5a6.25 6.25 0 0 0 12.5 0"/><path d="M12 17.75v2.5"/>',
  stop: '<rect x="7.5" y="7.5" width="9" height="9" rx="1.75" fill="currentColor" stroke="none"/>',
  "arrow-up": '<path d="M12 18.5v-13"/><path d="M6.75 10.75L12 5.5l5.25 5.25"/>',
  send: '<path d="M12 18.5v-13"/><path d="M6.75 10.75L12 5.5l5.25 5.25"/>',
  plus: '<path d="M12 5.75v12.5M5.75 12h12.5"/>',
  check: '<path d="M5.75 12.5l4 4 8.5-8.75"/>',
  x: '<path d="M6.75 6.75l10.5 10.5M17.25 6.75l-10.5 10.5"/>',
  edit: '<path d="M11.5 4.75H7a2.25 2.25 0 0 0-2.25 2.25v10A2.25 2.25 0 0 0 7 19.25h10A2.25 2.25 0 0 0 19.25 17v-4.5"/><path d="M17.6 4.15a1.6 1.6 0 0 1 2.25 2.25L12.5 13.75l-3 .75.75-3z"/>',
  flame: '<path d="M12 20.25a5.25 5.25 0 0 0 5.25-5.25c0-3.6-2.6-5.3-3.4-8.5-.6 1.9-1.6 3-2.85 3.4.1-2.5-.6-4.5-2-5.9.1 3.4-3.25 5.6-3.25 11a5.25 5.25 0 0 0 5.25 5.25z"/>',
  bolt: '<path d="M13 3.75L5.75 13.25h5.5l-.75 7 7.25-9.5h-5.5z"/>',
  volume: '<path d="M4.75 9.75v4.5h3.25l4.25 3.5V6.25L8 9.75z"/><path d="M15.75 9.25a4 4 0 0 1 0 5.5"/><path d="M18.25 6.75a7.5 7.5 0 0 1 0 10.5"/>',
  chevron: '<path d="M9.75 6.5l5.5 5.5-5.5 5.5"/>',
  "chevron-down": '<path d="M6.5 9.75l5.5 5.5 5.5-5.5"/>',
  sun: '<circle cx="12" cy="12" r="3.5"/><path d="M12 3.75v1.5M12 18.75v1.5M5.6 5.6l1.05 1.05M17.35 17.35l1.05 1.05M3.75 12h1.5M18.75 12h1.5M5.6 18.4l1.05-1.05M17.35 6.65l1.05-1.05"/>',
  moon: '<path d="M19.25 14.25A7.75 7.75 0 1 1 9.75 4.75a6.25 6.25 0 0 0 9.5 9.5z"/>',
  auto: '<circle cx="12" cy="12" r="7.75"/><path d="M12 4.25a7.75 7.75 0 0 1 0 15.5z" fill="currentColor" stroke="none"/>',
  refresh: '<path d="M19.25 12a7.25 7.25 0 0 1-12.6 4.9"/><path d="M4.75 12a7.25 7.25 0 0 1 12.6-4.9"/><path d="M17.5 3.75v3.5H14"/><path d="M6.5 20.25v-3.5H10"/>',
  list: '<path d="M9.25 7h10M9.25 12h10M9.25 17h10"/><path d="M4.75 7h.01M4.75 12h.01M4.75 17h.01"/>',
  activity: '<path d="M3.75 12h3.5l2.25-5.5 4 11 2.25-5.5h4.5"/>',
  heart: '<path d="M12 19.5s-7.25-4.3-7.25-9.75A3.9 3.9 0 0 1 12 7.6a3.9 3.9 0 0 1 7.25 2.15C19.25 15.2 12 19.5 12 19.5z"/>',
  target: '<circle cx="12" cy="12" r="7.75"/><circle cx="12" cy="12" r="3.75"/><path d="M12 12h.01"/>',
  box: '<path d="M4.25 8L12 4.25 19.75 8v8L12 19.75 4.25 16z"/><path d="M4.25 8L12 11.75 19.75 8M12 11.75v8"/>',
  pin: '<path d="M12 20.25s-5.75-5-5.75-10.25a5.75 5.75 0 0 1 11.5 0c0 5.25-5.75 10.25-5.75 10.25z"/><circle cx="12" cy="10" r="2.1"/>',
  user: '<circle cx="12" cy="8.5" r="3.5"/><path d="M5.25 19.75a6.75 6.75 0 0 1 13.5 0"/>',
  droplet: '<path d="M12 3.75s5.25 5.75 5.25 9.75a5.25 5.25 0 0 1-10.5 0C6.75 9.5 12 3.75 12 3.75z"/>',
  trash: '<path d="M4.75 7h14.5"/><path d="M9.75 7V5.25a.75.75 0 0 1 .75-.75h3a.75.75 0 0 1 .75.75V7"/><path d="M6.75 7l.75 11.6a1.5 1.5 0 0 0 1.5 1.4h6a1.5 1.5 0 0 0 1.5-1.4L17.25 7"/>',
  alert: '<path d="M10.7 4.9L3.4 17.6a1.5 1.5 0 0 0 1.3 2.25h14.6a1.5 1.5 0 0 0 1.3-2.25L13.3 4.9a1.5 1.5 0 0 0-2.6 0z"/><path d="M12 9.75v4"/><path d="M12 16.75v.01"/>',
  keyboard: '<rect x="3.25" y="6.25" width="17.5" height="11.5" rx="2"/><path d="M7 10.25h.01M10.33 10.25h.01M13.67 10.25h.01M17 10.25h.01M7.75 13.75h8.5"/>',
  clock: '<circle cx="12" cy="12" r="7.75"/><path d="M12 8v4l2.5 1.75"/>',
};

function icon(name, size = 18) {
  const svg = svgEl("svg", {
    viewBox: "0 0 24 24", width: size, height: size, fill: "none", stroke: "currentColor", "stroke-width": "1.5",
    "stroke-linecap": "round", "stroke-linejoin": "round", "aria-hidden": "true", class: "i",
  });
  svg.innerHTML = ICON_PATHS[name] || "";
  return svg;
}

function hydrateIcons(root = document) {
  for (const holder of $$("[data-icon]", root)) holder.replaceWith(icon(holder.dataset.icon, Number(holder.dataset.size) || 18));
}

// Tooltip ka text data-attributes mein rakhte hain; ek hi tooltip box sab jagah kaam aata hai.
function setTip(node, title, lines) {
  node.dataset.tipTitle = title;
  node.dataset.tip = lines.join("\n");
}

const clamp = (value, low, high) => Math.min(Math.max(value, low), high);
const shorten = (text, max) => (text.length > max ? text.slice(0, max - 1) + "…" : text);
const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;

function fmtMs(value) {
  if (value == null) return { value: "—", unit: "" };
  if (value >= 1000) return { value: (value / 1000).toFixed(1), unit: "s" };
  return { value: String(Math.round(value)), unit: "ms" };
}
const seconds = (ms) => (ms / 1000).toFixed(1) + " s";
const duration = (ms) => (ms < 1000 ? `${Math.round(ms)} ms` : seconds(ms));
function fmtUptime(total) {
  const h = Math.floor(total / 3600), m = Math.floor((total % 3600) / 60);
  if (h > 0) return h + "h " + String(m).padStart(2, "0") + "m";
  return m > 0 ? m + "m" : total + "s";
}
const clock = (ts) => new Date(ts * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
const fmtNum = (n) => (Number.isInteger(n) ? String(n) : n.toFixed(1));
const SHORT_UNITS = { glasses: "glasses", hours: "h", minutes: "min", "score 1-10": "/10" };

function saveSetting(key, value) { try { localStorage.setItem(key, value); } catch (e) { /* private window */ } }
function loadSetting(key, fallback) { try { return localStorage.getItem(key) ?? fallback; } catch (e) { return fallback; } }

async function getJSON(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

async function postJSON(url, body) {
  const response = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });
  let data = {};
  try { data = await response.json(); } catch (e) { /* khali jawab */ }
  if (!response.ok) {
    const error = new Error(data.message || data.error || `HTTP ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return data;
}

const SERVER_DOWN = "Dashboard server se jawab nahi aaya. Check karo ki dashboard.py chal raha hai.";

// ====================== Theme ======================
const THEMES = ["auto", "light", "dark"];
let theme = loadSetting("theme", "auto");
function applyTheme(mode) {
  if (mode === "auto") document.documentElement.removeAttribute("data-theme");
  else document.documentElement.dataset.theme = mode;
  const button = $("#themeBtn");
  button.replaceChildren(icon(mode === "light" ? "sun" : mode === "dark" ? "moon" : "auto"));
  const label = mode === "auto" ? "Theme: system" : `Theme: ${mode}`;
  button.setAttribute("aria-label", label);
  button.title = label;
}
$("#themeBtn").addEventListener("click", () => {
  theme = THEMES[(THEMES.indexOf(theme) + 1) % THEMES.length];
  saveSetting("theme", theme);
  applyTheme(theme);
});

// ====================== Tabs ======================
const VIEWS = ["assistant", "data", "notes", "system"];
let currentView = "assistant";

function showView(name, { focusTab = false } = {}) {
  if (!VIEWS.includes(name)) name = "assistant";
  currentView = name;
  for (const view of VIEWS) {
    $(`#view-${view}`).hidden = view !== name;
    const tab = $(`#tab-${view}`);
    tab.setAttribute("aria-selected", String(view === name));
    tab.tabIndex = view === name ? 0 : -1;
  }
  saveSetting("view", name);
  if (location.hash !== `#${name}`) history.replaceState(null, "", `#${name}`);
  if (focusTab) $(`#tab-${name}`).focus();
  if (name === "system" && lastStats) renderSystem(lastStats, true);
  if (name === "data" || name === "assistant") refreshOverview();
  if (name === "assistant") scrollChat();
}

for (const tab of $$(".tab")) tab.addEventListener("click", () => showView(tab.dataset.view));
window.addEventListener("hashchange", () => {
  const name = (location.hash || "").slice(1);
  if (VIEWS.includes(name) && name !== currentView) showView(name);
});
$(".tabs").addEventListener("keydown", (event) => {
  if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
  event.preventDefault();
  const index = VIEWS.indexOf(currentView);
  const next = event.key === "Home" ? 0 : event.key === "End" ? VIEWS.length - 1
    : (index + (event.key === "ArrowRight" ? 1 : -1) + VIEWS.length) % VIEWS.length;
  showView(VIEWS[next], { focusTab: true });
});

// ====================== Toast ======================
let toastTimer = null;
function toast(text, kind) {
  const node = $("#toast");
  node.textContent = text;
  node.dataset.kind = kind || "";
  node.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { node.hidden = true; }, kind === "error" ? 4200 : 2800);
}

// ====================== Tooltip ======================
const tip = $("#tip"), tipTitle = $("#tipTitle"), tipBody = $("#tipBody");
let tipTarget = null;

function showTip(target) {
  const lines = (target.dataset.tip || "").split("\n").filter(Boolean);
  if (!target.dataset.tipTitle && !lines.length) return;
  tipTitle.textContent = target.dataset.tipTitle || "";
  tipTitle.hidden = !target.dataset.tipTitle;
  tipBody.replaceChildren(...lines.map((line) => {
    const p = make("p");
    const cut = line.indexOf(": ");
    if (cut > 0 && cut < 24) p.append(make("strong", "", line.slice(0, cut + 1)), " " + line.slice(cut + 2));
    else p.textContent = line;
    return p;
  }));
  tip.hidden = false;
  tipTarget = target;
  target.setAttribute("aria-describedby", "tip");
  placeTip(target);
}

function placeTip(target) {
  const anchor = target.getBoundingClientRect(), box = tip.getBoundingClientRect();
  const x = clamp(anchor.left + anchor.width / 2 - box.width / 2, 8, window.innerWidth - box.width - 8);
  let y = anchor.top - box.height - 10;
  if (y < 8) y = anchor.bottom + 10;
  tip.style.transform = `translate(${Math.round(x)}px, ${Math.round(y)}px)`;
}

function hideTip() {
  if (tipTarget) tipTarget.removeAttribute("aria-describedby");
  tipTarget = null;
  tip.hidden = true;
}

const tipHost = (node) => (node.closest ? node.closest("[data-tip-title], [data-tip]") : null);
document.addEventListener("mouseover", (event) => { const t = tipHost(event.target); if (t && t !== tipTarget) showTip(t); });
document.addEventListener("mouseout", (event) => {
  const t = tipHost(event.target);
  if (t && !(event.relatedTarget && t.contains(event.relatedTarget))) hideTip();
});
document.addEventListener("focusin", (event) => { const t = tipHost(event.target); if (t) showTip(t); });
document.addEventListener("focusout", hideTip);
window.addEventListener("scroll", hideTip, { passive: true });

// ====================== Aapka data (Aaj sidebar + My data) ======================
let overviewData = null;
let thingFilter = "all";
let overviewBusy = false;

async function refreshOverview(force = false) {
  // Koi "Hata dein?" khula ho to normal refresh ruk jata hai; chat ke baad (force) zaroor taaza karo,
  // taaki purani row (jiski id ab kisi aur ko mil chuki ho) par galti se "Haan" na dab jaye.
  if (overviewBusy || (!force && $(".del-wrap .del-q"))) return;
  overviewBusy = true;
  try {
    overviewData = await getJSON("/api/overview");
    renderOverview(overviewData);
  } catch (error) {
    /* server band: engine pill dikhata hai */
  } finally {
    overviewBusy = false;
  }
}

function renderOverview(data) {
  const active = document.activeElement;
  const label = active && active !== document.body && active.getAttribute ? active.getAttribute("aria-label") : null;
  renderToday(data);
  renderData(data);
  if (label && document.activeElement === document.body) {
    const again = document.querySelector(`[aria-label="${CSS.escape(label)}"]`);
    if (again) again.focus();
  }
}

function emptyNote(text, example) {
  const p = make("p", "empty-note", text);
  if (example) { p.append(" Try: "); p.append(make("q", "", example)); }
  return p;
}

function checkbox(done, label, onClick) {
  const box = make("button", "checkbox");
  box.type = "button";
  box.setAttribute("aria-pressed", String(done));
  box.setAttribute("aria-label", label);
  box.append(icon("check", 14));
  if (done) box.disabled = true;
  else box.addEventListener("click", () => onClick(box));
  return box;
}

async function doAction(payload, button) {
  if (button) button.disabled = true;
  try {
    const data = await postJSON("/api/action", payload);
    if (!data.ok) {
      toast(data.message || "Ye nahi ho paya.", "error");
      if (button) button.disabled = false;
      return false;
    }
    toast(data.message);
    overviewData = data.overview;
    renderOverview(overviewData);
    return true;
  } catch (error) {
    toast(SERVER_DOWN, "error");
    if (button) button.disabled = false;
    return false;
  }
}

function habitCheckRow(habit) {
  const li = make("li", "check-row");
  li.dataset.done = String(habit.done_today);
  li.append(checkbox(habit.done_today, habit.done_today ? `${habit.name}: done today` : `Mark ${habit.name} done today`,
    (box) => doAction({ action: "check_in", habit: habit.name }, box)));
  const body = make("div", "check-body");
  body.append(make("span", "name", habit.name));
  const streak = make("span", "streak");
  streak.title = `${habit.streak}-day streak`;
  streak.append(icon("flame", 13), document.createTextNode(String(habit.streak)));
  li.append(body, streak);
  return li;
}

// "Hatao" button: pehle wahin poochhta hai "Hata dein? Haan / Nahi". Sirf "Haan" par server tak jata hai.
function deleteControl(kind, id, name, label = name) {
  const wrap = make("span", "del-wrap");
  const reset = () => {
    const button = make("button", "icon-btn del");
    button.type = "button";
    button.title = "Delete";
    button.setAttribute("aria-label", `Delete ${label}`);
    button.append(icon("trash", 14));
    button.addEventListener("click", (event) => { event.stopPropagation(); ask(); });
    wrap.replaceChildren(button);
  };
  const ask = () => {
    const yes = make("button", "btn xs danger", "Delete");
    const no = make("button", "btn xs", "Cancel");
    yes.type = no.type = "button";
    yes.addEventListener("click", async () => { yes.disabled = no.disabled = true; await deleteThing(kind, id, name, label); });
    no.addEventListener("click", reset);
    wrap.replaceChildren(make("span", "del-q", "Delete?"), yes, no);
    no.focus();  // galti se Enter dabe to kuch na hate
  };
  reset();
  return wrap;
}

async function deleteThing(kind, id, name, label) {
  try {
    const data = await postJSON("/api/delete", { kind, id, name, label });
    if (!data.ok) { toast(data.message || "Nahi hata paya.", "error"); resetRows(); return; }
    toast(data.message);
    overviewData = data.overview;
    renderOverview(overviewData);
  } catch (error) {
    toast(SERVER_DOWN, "error");
    resetRows();  // atka hua "Delete?" (band buttons) hatao, warna background refresh bhi ruka rehta
  }
}

function resetRows() {
  if (overviewData) renderOverview(overviewData);
  refreshOverview(true);
}

function taskCheckRow(task, className = "check-row") {
  const li = make(className === "check-row" ? "li" : "div", className);
  li.append(checkbox(false, `Mark ${task.title} done`, (box) => doAction({ action: "complete_task", task_id: task.id }, box)));
  const body = make("div", "check-body");
  body.append(make("span", "name", task.title));
  if (task.when) {
    const when = make("span", "when", task.status === "overdue" ? `${task.when} · overdue` : task.when);
    when.dataset.status = task.status;
    body.append(when);
  }
  li.append(body, deleteControl("task", task.id, task.title));
  return li;
}

function renderToday(data) {
  $("#todayLabel").textContent = data.today_label;
  const total = data.habits.length, done = data.counts.habits_done_today;
  const ring = $("#ringFg"), circumference = 2 * Math.PI * 26;
  ring.style.strokeDasharray = String(circumference);
  ring.style.strokeDashoffset = String(total ? circumference * (1 - done / total) : circumference);
  $("#ringValue").textContent = total ? `${done}/${total}` : "0";
  $("#ringNote").textContent = !total ? "No habits yet" : done === total ? "All habits done today" : `${total - done} left today`;

  const habits = $("#todayHabits");
  habits.replaceChildren(...data.habits.map(habitCheckRow));
  if (!data.habits.length) habits.append(emptyNote("No habits yet.", "walking naam ki habit shuru karo"));

  const tasks = $("#todayTasks"), pending = data.tasks.pending;
  tasks.replaceChildren(...pending.slice(0, 6).map((t) => taskCheckRow(t)));
  if (!pending.length) tasks.append(emptyNote("Nothing pending.", "kal 6 baje doodh lena yaad dilao"));
  else if (pending.length > 6) tasks.append(emptyNote(`+${pending.length - 6} more in My data`));
  const due = $("#dueCount");
  due.textContent = data.tasks.overdue ? `${data.tasks.overdue} overdue` : String(pending.length);
  due.dataset.kind = data.tasks.overdue ? "bad" : "";

  const healthHost = $("#todayHealth");
  healthHost.replaceChildren(...data.health.map((h) => {
    const tile = make("div", "hm");
    tile.append(make("span", "label", h.label));
    const value = make("span", "val", h.today == null ? "—" : fmtNum(h.today));
    if (h.today != null) value.append(make("small", "", SHORT_UNITS[h.unit] || h.unit));
    tile.append(value);
    if (h.kind === "hydration") {
      const plus = make("button", "icon-btn plus");
      plus.type = "button";
      plus.title = "+1 glass paani";
      plus.setAttribute("aria-label", "Ek glass paani aur jodo");
      plus.append(icon("plus", 14));
      plus.addEventListener("click", () => doAction({ action: "log_health", kind: "hydration", value: (h.today || 0) + 1 }, plus));
      tile.append(plus);
    }
    return tile;
  }));
}

function statCard(label, value, note, iconName) {
  const card = make("div", "stat");
  const head = make("span", "label");
  head.append(icon(iconName, 14), document.createTextNode(label));
  card.append(head, make("span", "value", String(value)), make("span", "note", note));
  return card;
}

function sparkline(values) {
  const W = 180, H = 34, pad = 4;
  const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, class: "spark", role: "img" });
  svgEl("line", { class: "base", x1: 0, x2: W, y1: H - pad, y2: H - pad }, svg);
  const numbers = values.filter((v) => v != null);
  svg.setAttribute("aria-label", numbers.length ? `Last ${values.length} days: ${values.map((v) => (v == null ? "no log" : v)).join(", ")}` : "No logs yet");
  if (!numbers.length) return svg;
  const max = Math.max(...numbers), min = Math.min(0, ...numbers);
  const x = (i) => pad + (i * (W - 2 * pad)) / Math.max(values.length - 1, 1);
  const y = (v) => H - pad - ((v - min) / (max - min || 1)) * (H - 2 * pad);
  let path = "";
  values.forEach((v, i) => {
    if (v == null) return;
    path += `${i === 0 || values[i - 1] == null ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)} `;
  });
  svgEl("path", { class: "line", d: path.trim() }, svg);
  values.forEach((v, i) => { if (v != null) svgEl("circle", { class: "pt", cx: x(i), cy: y(v), r: 2.4 }, svg); });
  return svg;
}

function smallTable(columns, rows) {
  const table = make("table", "data");
  const head = make("tr");
  for (const c of columns) head.append(make("th", "", c));
  const thead = make("thead");
  thead.append(head);
  const body = make("tbody");
  for (const row of rows) body.append(row);
  table.append(thead, body);
  return table;
}

const ACTIVE_STATUS = /read|padh|wear|use|lent|udhaar/i;
const DONE_STATUS = /finish|done|khatam|complete/i;

function renderData(data) {
  const c = data.counts;
  const nearest = data.goals.filter((g) => g.days_left >= 0).sort((a, b) => a.days_left - b.days_left)[0];
  $("#statStrip").replaceChildren(
    statCard("Habits", c.habits, `${c.habits_done_today} done today`, "flame"),
    statCard("Best streak", c.best_streak, "days in a row", "bolt"),
    statCard("Reminders", c.tasks_pending, c.tasks_overdue ? `${c.tasks_overdue} overdue` : "all on time", "list"),
    statCard("Goals", c.goals, nearest ? `next in ${nearest.days_left} days` : "none yet", "target"),
    statCard("Saved", c.things + c.items, `${c.things} things · ${c.items} places`, "box"),
    statCard("Contacts", c.contacts, "with nicknames", "user"),
  );

  // Habits: 14 din ka grid
  const habitsHost = $("#habitsList");
  habitsHost.replaceChildren(...data.habits.map((h) => {
    const row = make("div", "habit-row");
    row.append(make("span", "name", h.name));
    const days = make("div", "days");
    days.setAttribute("role", "img");
    days.setAttribute("aria-label", `${h.name}: pichhle 14 din mein ${h.grid.filter((d) => d.done).length} din`);
    h.grid.forEach((d, i) => {
      const cell = make("span", "day");
      cell.dataset.done = String(d.done);
      if (i === h.grid.length - 1) cell.dataset.today = "true";
      cell.title = `${d.day}: ${d.done ? "ho gayi" : "nahi"}`;
      days.append(cell);
    });
    const streak = make("span", "streak");
    streak.append(icon("flame", 13), document.createTextNode(`${h.streak} ${h.streak === 1 ? "day" : "days"}`));
    row.append(days, streak, make("span", "best", `best ${h.best}`), deleteControl("habit", h.id, h.name));
    return row;
  }));
  if (!data.habits.length) habitsHost.append(emptyNote("No habits tracked yet.", "reading naam ki habit shuru karo"));

  // Kaam
  const tasksHost = $("#tasksList");
  tasksHost.replaceChildren(...data.tasks.pending.map((t) => taskCheckRow(t, "task-row")));
  if (!data.tasks.pending.length) tasksHost.append(emptyNote("All done.", "parso subah 10 baje dentist yaad dilana"));
  $("#tasksDone").textContent = `${data.tasks.done} done`;

  // Health
  $("#healthList").replaceChildren(...data.health.map((h) => {
    const row = make("div", "health-row");
    const unit = SHORT_UNITS[h.unit] || h.unit;
    row.append(make("span", "name", h.label), sparkline(h.series));
    const today = make("span", "num", h.today == null ? "—" : fmtNum(h.today));
    if (h.today != null) today.append(make("small", "", ` ${unit}`));
    const avg = make("span", "num avg", h.avg_7 == null ? "—" : `${fmtNum(h.avg_7)}`);
    if (h.avg_7 != null) avg.append(make("small", "", ` avg`));
    row.append(today, avg);
    return row;
  }));

  // Goals
  const goalsHost = $("#goalsList");
  goalsHost.replaceChildren(...data.goals.map((g) => {
    const row = make("div", "goal-row");
    const top = make("div", "goal-top");
    const right = make("span", "del-wrap");
    right.append(make("span", "muted small", g.days_left >= 0 ? `${g.days_left} days left` : "past target"), deleteControl("goal", g.id, g.title));
    top.append(make("span", "name", g.title), right);
    const bar = make("div", "progress"), fill = make("span");
    fill.style.width = `${clamp(g.progress, 0, 100)}%`;
    bar.append(fill);
    bar.setAttribute("role", "img");
    bar.setAttribute("aria-label", `${g.progress}% samay beet gaya`);
    row.append(top, bar, make("span", "muted small", `Target ${g.target_date} · ${g.progress}% of time elapsed`));
    return row;
  }));
  if (!data.goals.length) goalsHost.append(emptyNote("No goals yet.", "July 2027 tak AI engineer banna hai, ye goal save karo"));

  renderThings(data.things);
  renderItems(data.items);

  // Contacts
  const contactsHost = $("#contactsList");
  contactsHost.replaceChildren(...data.contacts.map((person) => {
    const row = make("div", "contact-row");
    const initials = person.name.split(/\s+/).map((w) => w[0] || "").join("").slice(0, 2).toUpperCase();
    const body = make("div", "check-body");
    body.append(make("span", "name", person.name), make("span", "when", person.nicknames ? `aka ${person.nicknames}` : ""));
    row.append(make("span", "initials", initials), body, make("span", "muted", person.phone), deleteControl("contact", person.id, person.name));
    return row;
  }));
  if (!data.contacts.length) contactsHost.append(emptyNote("No contacts yet.", "mummy ka number 98xxxxxxxx save karo"));
}

function renderThings(things) {
  const filters = $("#thingFilters");
  const categories = [{ name: "all", count: things.list.length }, ...things.categories];
  if (!categories.some((c) => c.name === thingFilter)) thingFilter = "all";
  filters.replaceChildren(...categories.map((c) => {
    const pill = make("button", "fpill", `${c.name === "all" ? "Sab" : c.name} · ${c.count}`);
    pill.type = "button";
    pill.setAttribute("aria-pressed", String(c.name === thingFilter));
    pill.addEventListener("click", () => { thingFilter = c.name; renderThings(things); });
    return pill;
  }));
  const shown = things.list.filter((t) => thingFilter === "all" || t.category === thingFilter);
  const host = $("#thingsTable");
  if (!shown.length) { host.replaceChildren(emptyNote("Nothing saved yet.", "Nike Pegasus black joote rack mein hain")); return; }
  host.replaceChildren(smallTable(["Name", "Type", "Status", "Place", "Details", "Changed", ""], shown.map((t) => {
    const tr = make("tr");
    const status = make("td");
    if (t.status) {
      const badge = make("span", "status-badge", t.status);
      badge.dataset.kind = DONE_STATUS.test(t.status) ? "done" : ACTIVE_STATUS.test(t.status) ? "active" : "";
      status.append(badge);
    } else status.textContent = "—";
    const details = Object.entries(t.details || {}).map(([k, v]) => `${k}: ${v}`).join(", ");
    tr.append(make("td", "strong", t.name), make("td", "muted", t.category), status, make("td", "", t.place || "—"),
      make("td", "muted", details || "—"), make("td", "muted", shortDate(t.updated_at, false)));
    const del = make("td");
    del.append(deleteControl("thing", t.id, t.name));
    tr.append(del);
    return tr;
  })));
}

const MONTHS_SHORT = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
function shortDate(iso, withTime = true) {
  if (!iso) return "";
  const m = String(iso).match(/^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2}))?/);
  if (!m) return String(iso);
  const date = `${m[3]} ${MONTHS_SHORT[Number(m[2]) - 1]}`;
  return withTime && m[4] ? `${date} ${m[4]}:${m[5]}` : date;
}

function renderItems(items) {
  const query = $("#itemSearch").value.trim().toLowerCase();
  const shown = items.filter((i) => !query || i.name.toLowerCase().includes(query) || i.place.toLowerCase().includes(query));
  const host = $("#itemsTable");
  if (!shown.length) { host.replaceChildren(emptyNote(query ? "Kuch nahi mila." : "Kuch yaad nahi rakha.", query ? null : "passport office locker mein hai")); return; }
  host.replaceChildren(smallTable(["Item", "Place", "When", ""], shown.map((i) => {
    const tr = make("tr");
    const del = make("td");
    del.append(deleteControl("item", i.name, i.name));
    tr.append(make("td", "strong", i.name), make("td", "", i.place), make("td", "muted", shortDate(i.updated_at)), del);
    return tr;
  })));
}
$("#itemSearch").addEventListener("input", () => { if (overviewData) renderItems(overviewData.items); });

// ====================== Chat (assistant, tools ke saath) ======================
const SUGGESTIONS = [
  { k: "Habit", t: "walking ho gayi aaj" },
  { k: "Reminder", t: "kal shaam 6 baje doodh lena yaad dilao" },
  { k: "Find an item", t: "mera passport kahan hai" },
  { k: "Health", t: "aaj 8 glass paani piya" },
  { k: "Book", t: "Atomic Habits shelf 2 par hai, padh raha hoon" },
  { k: "From notes", t: "main kis company mein kaam karta hoon" },
];
const chat = { busy: false };
const ROUTE_TEXT = { shortcut: "Instant", model: "Model", chat: "Baat-cheet", confirm: "Pakka-check" };

function renderSuggestions() {
  $("#suggestions").replaceChildren(...SUGGESTIONS.map((s) => {
    const button = make("button", "suggestion");
    button.type = "button";
    button.append(make("span", "k", s.k), make("span", "", s.t));
    button.addEventListener("click", () => sendChat(s.t));
    return button;
  }));
}

function scrollChat() {
  const log = $("#chatLog");
  requestAnimationFrame(() => { log.scrollTop = log.scrollHeight; });
}

function updateEmpty() {
  $("#chatEmpty").hidden = $$("#chatLog .msg").length > 0;
}

function appendUser(text, ts) {
  const article = make("article", "msg user");
  article.append(make("div", "bubble", text), make("div", "msg-meta", clock(ts)));
  $("#chatLog").append(article);
  updateEmpty();
}

function botShell() {
  const article = make("article", "msg bot");
  const avatar = make("div", "avatar");
  avatar.append(icon("sparkle", 16));
  const main = make("div", "msg-main");
  article.append(avatar, main);
  return { article, main };
}

function chatTable(table) {
  const card = make("div", "table-card");
  card.append(make("div", "t-title", table.title));
  const scroll = make("div", "table-scroll");
  const el = make("table", "mini-table");
  const head = make("tr");
  for (const c of table.columns) head.append(make("th", "", c));
  const thead = make("thead");
  thead.append(head);
  const body = make("tbody");
  for (const row of table.rows.slice(0, 8)) {
    const tr = make("tr");
    for (const cell of row) tr.append(make("td", "", cell));
    body.append(tr);
  }
  el.append(thead, body);
  scroll.append(el);
  card.append(scroll);
  if (table.rows.length > 8) card.append(make("div", "table-more", `+${table.rows.length - 8} more in My data`));
  return card;
}

function traceRow(label, value) {
  const row = make("div", "row");
  row.append(make("b", "", label), make("span", "", value));
  return row;
}

function appendBot(entry) {
  const { article, main } = botShell();
  main.append(make("div", "bubble", entry.reply));
  if (entry.understood) main.append(make("p", "understood", `Samjha: “${entry.understood}”`));
  if (entry.tools.length) {
    const chips = make("div", "tool-chips");
    for (const tool of entry.tools) {
      const chip = make("span", "tool-chip");
      chip.dataset.ok = String(tool.ok);
      chip.append(icon(tool.ok ? "check" : "plus", 12), document.createTextNode(tool.name));
      chips.append(chip);
    }
    main.append(chips);
  }
  for (const table of entry.tables || []) main.append(chatTable(table));
  if (entry.pending) main.append(confirmCard(entry.pending));

  // "Kaise kiya": seekhne ke liye poora raasta
  const trace = make("details", "trace");
  const summary = make("summary");
  summary.append(icon("chevron", 12), document.createTextNode("Kaise kiya"));
  const body = make("div", "trace-body");
  const routeText = entry.route === "shortcut" ? `Instant shortcut (${entry.shortcut}) — model nahi bulaya`
    : entry.route === "confirm" ? "Hatane ke sawal ka jawab — model nahi bulaya, code ne seedha kiya"
    : entry.route === "chat" ? "Baat-cheet — koi tool nahi diya" : `Model ko ${entry.offered.length} tool diye: ${entry.offered.join(", ")}`;
  body.append(traceRow("Raasta", routeText));
  if (entry.reason) body.append(traceRow("Router", entry.reason));
  if (entry.when) body.append(traceRow("Samay samjha", entry.when));
  body.append(traceRow("Time", `${duration(entry.ms)} · ${plural(entry.llm_calls, "model call", "model calls")}`));
  for (const tool of entry.tools) {
    body.append(make("pre", "", `${tool.name}(${JSON.stringify(tool.arguments)})\n→ ${shorten(JSON.stringify(tool.result), 500)}`));
  }
  trace.append(summary, body);
  main.append(trace);

  const meta = make("div", "msg-meta");
  const route = make("span", "route");
  route.dataset.route = entry.route;
  if (entry.route === "shortcut") route.append(icon("bolt", 12));
  route.append(document.createTextNode(`${ROUTE_TEXT[entry.route] || "Model"} · ${duration(entry.ms)}`));
  const play = make("button", "link-btn");
  play.type = "button";
  play.setAttribute("aria-label", "Jawab suno");
  play.append(icon("volume", 13), document.createTextNode("Suno"));
  play.addEventListener("click", () => speak(entry.reply, true));
  meta.append(make("span", "", clock(entry.ts)), route, play);
  main.append(meta);
  $("#chatLog").append(article);
  updateEmpty();
}

const RESOLVED_TEXT = { yes: "Deleted.", no: "Kept.", stale: "This question expired.", dropped: "Question dismissed.", none: "Closed." };

function confirmCard(pending) {
  const card = make("div", "confirm-card");
  card.dataset.token = pending.token || "";
  const text = make("div", "cc-text");
  const words = make("div");
  words.append(make("span", "", "Delete this?"), make("strong", "", pending.label));
  text.append(icon("alert", 16), words);
  const actions = make("div", "cc-actions");
  if (pending.resolved) {
    card.dataset.state = "done";
    actions.append(make("span", "cc-state", RESOLVED_TEXT[pending.resolved] || "Sawal band."));
  } else {
    const yes = make("button", "btn sm danger");
    yes.type = "button";
    yes.append(icon("trash", 14), document.createTextNode("Yes, delete"));
    yes.addEventListener("click", () => sendChat("haan, hata do", { confirmToken: pending.token }));
    const no = make("button", "btn sm", "Keep");
    no.type = "button";
    no.addEventListener("click", () => sendChat("nahi", { confirmToken: pending.token }));
    actions.append(yes, no);
  }
  card.append(text, actions);
  return card;
}

function latestOpenToken() {
  const cards = $$(".confirm-card:not([data-state='done'])");
  return cards.length ? cards[cards.length - 1].dataset.token || null : null;
}

function closeConfirmCards() {
  // Naya message gaya: purane "pakka?" sawal band (server bhi unhe band maanta hai).
  for (const card of $$(".confirm-card:not([data-state='done'])")) {
    card.dataset.state = "done";
    for (const button of $$("button", card)) button.disabled = true;
  }
}

function appendError(text, retry) {
  const { article, main } = botShell();
  const bubble = make("div", "bubble", text);
  bubble.dataset.kind = "error";
  if (retry) {
    bubble.append(" ");
    const again = make("button", "link-btn", "Dobara bhejo");
    again.type = "button";
    again.addEventListener("click", () => { article.remove(); retry(); });
    bubble.append(again);
  }
  main.append(bubble);
  $("#chatLog").append(article);
}

function showTyping() {
  const { article, main } = botShell();
  article.classList.add("typing");
  const bubble = make("div", "bubble");
  bubble.setAttribute("aria-label", "Assistant soch raha hai");
  for (let i = 0; i < 3; i += 1) bubble.append(make("span", "dot3"));
  const elapsed = make("span", "elapsed", "");
  bubble.append(elapsed);
  main.append(bubble);
  $("#chatLog").append(article);
  const started = performance.now();
  const timer = setInterval(() => {
    const ms = performance.now() - started;
    if (ms > 700) elapsed.textContent = seconds(ms);
  }, 100);
  return { remove() { clearInterval(timer); article.remove(); } };
}

function setComposerBusy(busy) {
  chat.busy = busy;
  $("#sendBtn").disabled = busy || !$("#chatInput").value.trim();
  $("#newChatBtn").disabled = busy;
}

async function sendChat(text, opts = {}) {
  text = text.trim();
  if (!text || chat.busy) return;
  cancelAutoSend();
  stopSpeaking();
  // Screen par jo "pakka?" sawal khula hai uska token ("" = koi nahi). Doosre tab ka sawal is "haan" se nahi hatega.
  const confirmToken = opts.confirmToken || latestOpenToken() || "";
  closeConfirmCards();
  const input = $("#chatInput");
  input.value = "";
  input.classList.remove("interim");
  autosize(input);
  setComposerBusy(true);
  appendUser(text, Date.now() / 1000);
  const typing = showTyping();
  scrollChat();
  try {
    const body = { text, confirm_token: confirmToken };
    const entry = await postJSON("/api/assistant", body);
    typing.remove();
    appendBot(entry);
    speak(entry.reply);
    refreshOverview(true);
  } catch (error) {
    typing.remove();
    appendError(error.status === 502 ? error.message : SERVER_DOWN, () => sendChat(text, opts));
  } finally {
    setComposerBusy(false);
    scrollChat();
    input.focus();
  }
}

async function loadChatHistory() {
  try {
    const data = await getJSON("/api/assistant/history");
    for (const entry of data.messages) {
      try { appendUser(entry.text, entry.ts); appendBot({ tools: [], tables: [], offered: [], ...entry }); }
      catch (error) { /* ek kharab entry poori chat na rok de */ }
    }
    updateEmpty();
    scrollChat();
  } catch (error) { /* pehli baar: khali chat */ }
}

function autosize(textarea) {
  textarea.style.height = "auto";
  textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px`;
}

$("#chatInput").addEventListener("input", (event) => {
  autosize(event.target);
  $("#sendBtn").disabled = chat.busy || !event.target.value.trim();
});
$("#chatInput").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    $("#chatForm").requestSubmit();
  }
});
$("#chatForm").addEventListener("submit", (event) => {
  event.preventDefault();
  sendChat($("#chatInput").value);
});
$("#newChatBtn").addEventListener("click", async () => {
  if (chat.busy) return;
  try {
    await postJSON("/api/assistant/reset", {});
    for (const node of $$("#chatLog .msg")) node.remove();
    updateEmpty();
    toast("New chat started. Your saved data is unchanged.");
  } catch (error) {
    toast(SERVER_DOWN, "error");
  }
});

// ====================== Awaaz: bolkar jawab (Mac `say`) ======================
let speakingOnServer = false;
const HAS_DEVANAGARI = /[ऀ-ॿ]/;

function postSpeak(text) {
  return fetch("/api/speak", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) });
}

function stopSpeaking() {
  if ("speechSynthesis" in window) speechSynthesis.cancel();
  if (speakingOnServer) { postSpeak("").catch(() => {}); speakingOnServer = false; }
}

async function speak(text, force = false) {
  if ((!$("#speakToggle").checked && !force) || !text) return;
  stopSpeaking();
  const engine = $("#ttsEngine") ? $("#ttsEngine").value : "browser";
  if (engine === "browser" && "speechSynthesis" in window) {
    speakInBrowser(text);
    return;
  }
  // System voice (Mac `say`)
  try {
    const response = await postSpeak(text);
    if (response.ok) { speakingOnServer = true; return; }
  } catch (error) { /* server tak nahi pahuncha: browser ki awaaz try karo */ }
  speakInBrowser(text);
}

function speakInBrowser(text) {
  if (!("speechSynthesis" in window)) return;
  const voices = speechSynthesis.getVoices();
  const hindi = HAS_DEVANAGARI.test(text);
  // Sabse natural awaaz: Premium > Enhanced > Indian > koi bhi. Offline (localService) wali pehle: text bahar na jaye.
  const want = hindi ? "hi" : "en";
  const score = (v) => {
    const lang = v.lang.toLowerCase().replace("_", "-");
    if (!lang.startsWith(want)) return -1;
    return (/premium/i.test(v.name) ? 8 : /enhanced/i.test(v.name) ? 4 : 0) +
           (lang.endsWith("-in") ? 2 : 0) + (v.localService ? 1 : 0);
  };
  const chosen = voices.filter((v) => score(v) >= 0).sort((a, b) => score(b) - score(a))[0] || null;
  const utterance = new SpeechSynthesisUtterance(text);
  if (chosen) { utterance.voice = chosen; utterance.lang = chosen.lang; } else { utterance.lang = hindi ? "hi-IN" : "en-IN"; }
  utterance.rate = 1.0;
  utterance.pitch = 1.0;
  speechSynthesis.speak(utterance);
}

// ====================== Awaaz se likhna: Browser ya offline Whisper, LIVE text ke saath ======================
// Dono mein bolte waqt shabd usi waqt dikhte hain. Bolna khatam hone par 2 second ruk kar bhejte hain
// (galat suna ho to Esc dabao ya text theek karo). Whisper chup hote hi khud ruk jaata hai.
const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const voice = { active: null, recognizer: null, rec: null, whisperOk: false, autoSend: null, error: false };
const MIC_ERRORS = {
  "not-allowed": "Microphone access was blocked. Allow it from the address bar.",
  "no-speech": "Didn't hear anything. Try again.",
  "audio-capture": "No microphone found.",
  "network": "Browser speech service unreachable (needs internet). Choose Whisper (offline).",
};
const AUTO_SEND_SECONDS = 2;
const WHISPER_LANG = "auto";        // server par Hinglish prompt ke saath: Hindi/Hinglish dono Roman Hinglish mein
const PARTIAL_EVERY_MS = 900;       // bolte waqt itni der mein ek baar adhoora text
const SILENCE_STOP_MS = 1300;       // itna chup = bolna khatam
const MAX_RECORD_MS = 30000;

function setMicState(button, state) {
  button.dataset.state = state;
  button.setAttribute("aria-pressed", String(state === "listening"));
  button.replaceChildren(icon(state === "listening" ? "stop" : "mic", 18));
}

// Har mic ka apna "context": kis input mein likhna hai, kise live dikhana hai, bhejna kaise hai, status kahan.
const MIC_CONTEXTS = {
  chat: {
    button: () => $("#micBtn"), input: () => $("#chatInput"), box: () => $("#chatForm .composer-box"),
    send: (text) => sendChat(text),
    status: (text, kind) => { const n = $("#voiceStatus"); n.textContent = text || ""; n.dataset.kind = kind || ""; },
  },
  notes: {
    button: () => $("#notesMic"), input: () => $("#notesInput"), box: () => $("#notesInput"),
    send: (text) => askNotes(text),  // seedha poochho: chal raha jawab "Stop" na ho jaye
    status: (text, kind) => setNotesStatus(text || "", kind === "error" ? "error" : ""),
  },
};

function setLive(context, on) {
  const box = context.box();
  if (on) box.dataset.live = "true"; else delete box.dataset.live;
  $("#voiceLevel").hidden = !(on && context === MIC_CONTEXTS.chat);
  if (!on) showLevel(0);
}

function showLevel(rms) {
  $("#voiceLevel > span").style.width = `${Math.min(100, Math.round(rms * 900))}%`;
}

function writeLive(context, text, interim) {
  const input = context.input();
  input.value = text;
  input.classList.toggle("interim", Boolean(interim));
  if (input.tagName === "TEXTAREA") autosize(input);
  if (context === MIC_CONTEXTS.chat) $("#sendBtn").disabled = chat.busy || !text.trim();
}

function toggleVoice(name) {
  if (voice.autoSend) cancelAutoSend("Send cancelled. Edit and press Enter.");
  if (voice.active) { stopVoice(); return; }  // chal rahi recording / start / final: sab ek hi click se ruke
  stopSpeaking();
  const context = MIC_CONTEXTS[name];
  voice.error = false;
  if ($("#voiceEngine").value === "whisper" && voice.whisperOk) {
    fetch("/api/voice/warm", { method: "POST" }).catch(() => {});
    startWhisper(context);
  }
  else startBrowserVoice(context);
}

function contextBusy(context) {
  return context === MIC_CONTEXTS.chat ? chat.busy : notesUi.busy;
}

function finishVoice(context) {
  voice.active = null;
  voice.recognizer = null;
  voice.rec = null;
  voice.session = null;
  setLive(context, false);
  setMicState(context.button(), "idle");
}

// Bolna khatam: text dikhao, 2 second ruko, phir bhejo. Beech mein kuch type kiya ya Esc = mat bhejo.
function armAutoSend(context, text) {
  cancelAutoSend();
  if (!text.trim()) return;
  if (context === MIC_CONTEXTS.chat && latestOpenToken()) {
    // "Pakka hata doon?" khula hai: adhoora "haan…" galti se na chala jaye. Khud dekh kar bhejo.
    context.status("A delete question is open: check the text and press Enter, or use the card buttons.");
    return;
  }
  let left = AUTO_SEND_SECONDS;
  const tick = () => context.status(`Sending in ${left}s… (Esc or typing cancels)`, "live");
  tick();
  voice.autoSend = {
    context,
    timer: setInterval(() => {
      if (left > 0) left -= 1;
      if (left > 0) { tick(); return; }
      if (contextBusy(context)) { context.status("Waiting for the previous reply…", "live"); return; }
      const value = context.input().value.trim();
      cancelAutoSend();
      if (value) context.send(value);
    }, 1000),
  };
}

function cancelAutoSend(message) {
  if (!voice.autoSend) return;
  clearInterval(voice.autoSend.timer);
  const { context } = voice.autoSend;
  voice.autoSend = null;
  context.status(message || "");
}

for (const context of Object.values(MIC_CONTEXTS)) {
  const input = context.input();
  input.addEventListener("keydown", (event) => {
    if (!voice.autoSend || voice.autoSend.context !== context || event.key === "Enter") return;
    cancelAutoSend("Send cancelled. Edit and press Enter.");
  });
  input.addEventListener("pointerdown", () => {
    if (voice.autoSend && voice.autoSend.context === context) cancelAutoSend("Send cancelled. Edit and press Enter.");
  });
}

async function fixText(text) {
  try {
    const data = await postJSON("/api/voice/fix", { text });
    return data.text || text;
  } catch (error) {
    return text;
  }
}

// ---------- Browser (Chrome/Safari): turant live text, par awaaz Google/Apple ko jaati hai ----------
function startBrowserVoice(context) {
  if (!Recognition) {
    context.status("This browser has no speech input. Use Chrome or Safari, or choose Whisper (offline).", "error");
    return;
  }
  const recognizer = new Recognition();
  recognizer.lang = $("#micLang").value;
  recognizer.interimResults = true;
  let finalText = "";
  recognizer.onresult = (event) => {
    let interim = "";
    finalText = "";  // har baar poori list se dobara banao (pichhle tukde do baar na judein)
    for (const result of event.results) {
      if (result.isFinal) finalText += result[0].transcript; else interim += result[0].transcript;
    }
    writeLive(context, `${finalText} ${interim}`.trim(), Boolean(interim));
    context.status("Listening…", "live");
  };
  recognizer.onerror = (event) => {
    voice.error = true;
    context.status(MIC_ERRORS[event.error] || `Mic error: ${event.error}`, "error");
  };
  recognizer.onend = async () => {
    finishVoice(context);
    const text = (finalText || context.input().value).trim();
    if (!text) { if (!voice.error) context.status(""); return; }
    const fixed = await fixText(text);  // "phoon" -> "phone" jaise galat-sune shabd
    writeLive(context, fixed, false);
    armAutoSend(context, fixed);
  };
  voice.active = context;
  voice.recognizer = recognizer;
  setMicState(context.button(), "listening");
  setLive(context, true);
  writeLive(context, "", true);
  context.status("Listening…", "live");
  recognizer.start();
}

// ---------- Whisper (offline): mic ki awaaz 16 kHz WAV mein, har ~1 s adhoora text, chup hote hi final ----------
function downsampleTo16k(chunks, inputRate) {
  const total = chunks.reduce((n, c) => n + c.length, 0);
  const all = new Float32Array(total);
  let pos = 0;
  for (const c of chunks) { all.set(c, pos); pos += c.length; }
  const ratio = inputRate / 16000;
  const out = new Int16Array(Math.floor(total / ratio));
  for (let i = 0; i < out.length; i += 1) {
    const start = Math.floor(i * ratio), end = Math.min(Math.floor((i + 1) * ratio), total);
    let sum = 0;
    for (let j = start; j < end; j += 1) sum += all[j];
    const v = Math.max(-1, Math.min(1, sum / Math.max(end - start, 1)));
    out[i] = v < 0 ? v * 0x8000 : v * 0x7fff;
  }
  return out;
}

function wavBlob(samples, rate = 16000) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const text = (offset, value) => { for (let i = 0; i < value.length; i += 1) view.setUint8(offset + i, value.charCodeAt(i)); };
  text(0, "RIFF"); view.setUint32(4, 36 + samples.length * 2, true); text(8, "WAVE");
  text(12, "fmt "); view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true);
  view.setUint32(24, rate, true); view.setUint32(28, rate * 2, true); view.setUint16(32, 2, true); view.setUint16(34, 16, true);
  text(36, "data"); view.setUint32(40, samples.length * 2, true);
  new Int16Array(buffer, 44).set(samples);
  return new Blob([buffer], { type: "audio/wav" });
}

async function postAudio(blob, partial) {
  const langSel = $("#micLang") ? $("#micLang").value : "en-IN";
  // "auto" kabhi Hindi ko Gujarati maan leta tha (mili-juli lipi). Test mein "en" + Hinglish prompt ne English, Hinglish
  // aur Hindi teeno ko sahi Roman mein likha; "hi" chhoti English lines bigaad deta tha. Isliye Hinglish/English = "en".
  const whisperLang = langSel === "hi-IN" ? "hi" : "en";
  const response = await fetch(`/api/transcribe?lang=${whisperLang}&partial=${partial ? 1 : 0}`, {
    method: "POST", headers: { "Content-Type": "audio/wav" }, body: blob,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.message || "Whisper se jawab nahi aaya.");
  return data;
}

async function startWhisper(context) {
  // Session pehle hi bana do (sync), taaki permission ke beech doosra click "rok do" maana jaye, naya recorder nahi.
  const session = { context, cancelled: false, rec: null };
  voice.active = context;
  voice.session = session;
  setMicState(context.button(), "working");
  context.status("Starting microphone…", "live");
  // AudioContext click ke turant baad banao (Safari ko user ka click chahiye), mic ki permission baad mein.
  const AudioCtx = window.AudioContext || window.webkitAudioContext;
  const ctx = new AudioCtx();
  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: false, autoGainControl: true, channelCount: 1 } });
  } catch (error) {
    ctx.close().catch(() => {});
    if (voice.session === session) { finishVoice(context); context.status("Microphone access was blocked. Allow it in the browser.", "error"); }
    return;
  }
  if (session.cancelled || voice.session !== session) {  // permission ke beech user ne rok diya
    stream.getTracks().forEach((track) => track.stop());
    ctx.close().catch(() => {});
    return;
  }
  if (ctx.state === "suspended") await ctx.resume().catch(() => {});
  const source = ctx.createMediaStreamSource(stream);
  const processor = ctx.createScriptProcessor(4096, 1, 1);
  const mute = ctx.createGain();
  mute.gain.value = 0;  // apni awaaz speaker mein wapas na aaye
  source.connect(processor);
  processor.connect(mute);
  mute.connect(ctx.destination);
  const rec = { session, ctx, stream, source, processor, chunks: [], rate: ctx.sampleRate, started: performance.now(), speech: false,
    loudFrames: 0, frames: 0, silenceMs: 0, floor: null, peak: 0, inFlight: null, lastPartialAt: 0, stopped: false, text: "" };
  session.rec = rec;
  processor.onaudioprocess = (event) => {
    if (rec.stopped) return;
    const data = new Float32Array(event.inputBuffer.getChannelData(0));
    rec.chunks.push(data);
    rec.frames += 1;
    let sum = 0;
    for (let i = 0; i < data.length; i += 1) sum += data[i] * data[i];
    const rms = Math.sqrt(sum / data.length);
    showLevel(rms);
    // Shor (floor) dheere seekho, pehle ~250 ms sirf seekho; bolna = lagatar 3 tukde (~250 ms) shor se upar.
    const loud = rec.floor !== null && rms > Math.max(0.006, rec.floor * 2.2);
    if (!rec.speech) rec.floor = rec.floor === null ? rms : Math.min(rec.floor * 1.01 + 0.0001, 0.92 * rec.floor + 0.08 * rms);  // bolte waqt floor freeze: apni hi awaaz se threshold na chadhe
    rec.peak = Math.max(rec.peak * 0.995, rms);
    rec.loudFrames = loud && rec.frames > 3 ? rec.loudFrames + 1 : 0;
    if (rec.loudFrames >= 3) { rec.speech = true; rec.silenceMs = 0; }
    const quiet = rms < Math.max(rec.floor * 1.6, rec.peak * 0.15);  // shor wale kamre mein bhi khamoshi pakde
    if (rec.speech && quiet) rec.silenceMs += (data.length / rec.rate) * 1000;
    else if (rec.speech && loud) rec.silenceMs = 0;
    const elapsed = performance.now() - rec.started;
    if ((rec.speech && rec.silenceMs > SILENCE_STOP_MS) || elapsed > MAX_RECORD_MS || (!rec.speech && elapsed > 8000)) {
      finishWhisper(rec, context);  // sirf ISI recorder ko band karo, kisi aur session ko nahi
    } else if (rec.speech && !rec.inFlight && performance.now() - rec.lastPartialAt > PARTIAL_EVERY_MS) {
      sendPartial(rec, context);
    }
  };
  voice.rec = rec;
  setMicState(context.button(), "listening");
  setLive(context, true);
  writeLive(context, "", true);
  context.status("Listening… (stops when you pause)", "live");
}

// Har partial par poori recording dobara 16 kHz banana O(n^2) tha. Ab sirf naye tukde badalte hain, purane yaad rehte hain.
function currentWav(rec) {
  rec.done = rec.done || { chunks: 0, parts: [], length: 0, rest: new Float32Array(0) };
  const state = rec.done;
  if (state.chunks < rec.chunks.length) {
    const fresh = [state.rest, ...rec.chunks.slice(state.chunks)];
    state.chunks = rec.chunks.length;
    const ratio = rec.rate / 16000;
    const total = fresh.reduce((n, c) => n + c.length, 0);
    const usable = Math.floor(Math.floor(total / ratio) * ratio);  // jo poore 16 kHz samples ban sakein
    const converted = downsampleTo16k(fresh, rec.rate);
    const all = new Float32Array(total);
    let pos = 0;
    for (const c of fresh) { all.set(c, pos); pos += c.length; }
    state.rest = all.slice(usable);  // bacha hua adhoora hissa agli baar
    state.parts.push(converted);
    state.length += converted.length;
  }
  const joined = new Int16Array(state.length);
  let offset = 0;
  for (const part of state.parts) { joined.set(part, offset); offset += part.length; }
  return wavBlob(joined);
}

function sendPartial(rec, context) {
  rec.lastPartialAt = performance.now();
  rec.inFlight = postAudio(currentWav(rec), true)
    .then((data) => {
      if (!rec.stopped && !rec.session.cancelled && data.text) {
        rec.text = data.text;
        rec.written = data.text;
        writeLive(context, data.text, true);
      }
    })
    .catch(() => { /* adhoora text na mila to koi baat nahi, final aayega */ })
    .finally(() => { rec.inFlight = null; });
}

async function finishWhisper(rec, context) {
  if (rec.stopped) return;  // ek recorder sirf ek baar band hota hai
  rec.stopped = true;
  try { rec.processor.disconnect(); rec.source.disconnect(); } catch (error) { /* pehle hi band */ }
  rec.stream.getTracks().forEach((track) => track.stop());
  rec.ctx.close().catch(() => {});
  setLive(context, false);
  if (!rec.speech || rec.session.cancelled) {
    finishVoice(context);
    if (!rec.session.cancelled) { writeLive(context, "", false); context.status("Didn't hear anything. Try again.", "error"); }
    return;
  }
  setMicState(context.button(), "working");
  context.status("Finishing… (Esc cancels)", "live");
  if (rec.inFlight) await rec.inFlight;
  const input = context.input();
  try {
    const data = await postAudio(currentWav(rec), false);
    if (voice.session === rec.session) finishVoice(context);
    if (rec.session.cancelled) return;  // "working" ke beech Esc ya mic dabaya: kuch mat likho, mat bhejo
    if (rec.written !== undefined && input.value !== rec.written) {  // user ne beech mein text theek kiya
      context.status("Kept your edited text. Press Enter to send.");
      input.classList.remove("interim");
      return;
    }
    if (!data.text) { writeLive(context, "", false); context.status("Couldn't make that out. Please say it again.", "error"); return; }
    writeLive(context, data.text, false);
    armAutoSend(context, data.text);
  } catch (error) {
    if (voice.session === rec.session) finishVoice(context);
    if (rec.session.cancelled) return;
    writeLive(context, rec.text || "", false);
    context.status(error.message || "Whisper se jawab nahi aaya.", "error");
  }
}

function stopVoice() {
  if (voice.recognizer) { voice.recognizer.stop(); return; }
  const session = voice.session;
  if (!session) return;
  const rec = session.rec;
  if (rec && !rec.stopped) { finishWhisper(rec, session.context); return; }  // bolna khatam: final banao
  // Mic shuru ho raha tha, ya final ban raha tha: rok do (koi text nahi likha jayega, kuch nahi bheja jayega)
  session.cancelled = true;
  finishVoice(session.context);
  session.context.status("Stopped.");
}

$("#micBtn").addEventListener("click", () => toggleVoice("chat"));
$("#notesMic").addEventListener("click", () => toggleVoice("notes"));

function syncLangSelect() {
  // Bhasha dono engines ke liye chalti hai (Whisper ko bhi batate hain, andaza nahi lagwate).
  $("#micLang").disabled = false;
  $("#micLang").title = "";
}

function updateVoiceOptions(stats) {
  voice.whisperOk = Boolean(stats.whisper_ok);
  const option = $("#voiceEngine option[value=whisper]");
  option.disabled = !voice.whisperOk;
  option.textContent = voice.whisperOk ? `Whisper (offline · ${stats.whisper_model})` : "Whisper (model taiyar nahi)";
  if (!voice.whisperOk && $("#voiceEngine").value === "whisper") $("#voiceEngine").value = "browser";
  syncLangSelect();
}

// ====================== Notes se sawal (streaming) ======================
const notesUi = { busy: false, controller: null, ticker: null, startedAt: 0 };
const NOTES_CHIPS = ["What are my career goals?", "Where do I work?", "Mera hometown kya hai?"];
const stageEl = (name) => $(`#stages li[data-stage="${name}"]`);

function setStage(name, state, text) {
  const li = stageEl(name);
  li.dataset.state = state;
  if (text !== undefined) li.querySelector(".time").textContent = text;
}

function setNotesStatus(text, kind) {
  const node = $("#notesStatus");
  node.textContent = text;
  node.dataset.kind = kind || "";
}

function setNotesBusy(busy) {
  notesUi.busy = busy;
  const button = $("#notesBtn");
  button.textContent = busy ? "Stop" : "Ask";
  button.dataset.mode = busy ? "stop" : "ask";
  $("#notesInput").readOnly = busy;
}

function startTicker() {
  notesUi.startedAt = performance.now();
  notesUi.ticker = setInterval(() => {
    const active = $('#stages li[data-state="active"]');
    if (active) active.querySelector(".time").textContent = seconds(performance.now() - notesUi.startedAt);
  }, 100);
}
function stopTicker() { clearInterval(notesUi.ticker); notesUi.ticker = null; }

function showSources(passages, searchMs) {
  setStage("search", "done", seconds(searchMs));
  setStage("first", "active");
  $("#sourcesTitle").textContent = `Passages the model read (${passages.length})`;
  $("#sourcesList").replaceChildren(...passages.map((p) => {
    const li = make("li");
    const score = make("span", "src-score"), meter = make("span", "meter"), fill = make("span");
    fill.style.width = `${clamp(p.score, 0, 1) * 100}%`;
    meter.append(fill);
    score.append(meter, make("span", "", p.score.toFixed(2)));
    setTip(li, p.file, [shorten(p.text, 420), `Match score: ${p.score.toFixed(2)}`]);
    li.tabIndex = 0;
    li.append(make("span", "src-file", p.file), score, make("span", "src-text", p.text.replace(/\s+/g, " ")));
    return li;
  }));
  $("#sources").hidden = false;
}

function handleEvent(event, answerText) {
  if (event.type === "sources") {
    showSources(event.passages, event.search_ms);
    setNotesStatus("Reading your notes…");
  } else if (event.type === "token") {
    if (!answerText.started) {
      answerText.started = true;
      setStage("first", "done", seconds(performance.now() - notesUi.startedAt));
      setStage("write", "active");
      setNotesStatus("Writing…");
    }
    answerText.node.textContent += event.text;
  } else if (event.type === "done") {
    finishAnswer(event);
  } else if (event.type === "error") {
    $("#stages").hidden = true; // error mein progress dikhana bekaar hai
    setNotesStatus(event.message, "error");
  }
}

function finishAnswer(done) {
  speak($("#notesAnswerText").textContent);
  setStage("search", "done", seconds(done.search_ms));
  setStage("first", "done", seconds(done.first_word_ms));
  setStage("write", "done", seconds(done.total_ms - done.first_word_ms));
  const speed = done.tokens_per_s ? `, writing at ${Math.round(done.tokens_per_s)} tokens/s` : "";
  const summary = `Done in ${seconds(done.total_ms)}${speed}.`;
  setNotesStatus(done.dont_know ? summary + " The notes don't seem to cover this question." : summary);
}

async function readStream(response, answerText) {
  const reader = response.body.getReader(), decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let end;
    while ((end = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, end);
      buffer = buffer.slice(end + 2);
      if (frame.startsWith("data: ")) handleEvent(JSON.parse(frame.slice(6)), answerText);
    }
  }
}

async function askNotes(question) {
  cancelAutoSend();
  stopSpeaking();
  setNotesBusy(true);
  notesUi.controller = new AbortController();
  $("#notesAsked").textContent = question;
  const answerText = { node: $("#notesAnswerText"), started: false };
  answerText.node.textContent = "";
  $("#notesAnswer").hidden = false;
  $("#notesCaret").hidden = false;
  $("#stages").hidden = false;
  $("#sources").hidden = true;
  setStage("search", "active", "0.0 s");
  setStage("first", "pending", "–");
  setStage("write", "pending", "–");
  setNotesStatus("Searching your notes…");
  startTicker();
  try {
    const response = await fetch("/api/ask", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }), signal: notesUi.controller.signal,
    });
    if (!response.ok || !response.body) throw new Error("bad response");
    await readStream(response, answerText);
  } catch (error) {
    if (error.name === "AbortError") setNotesStatus("Stopped.");
    else setNotesStatus(SERVER_DOWN, "error");
  } finally {
    stopTicker();
    $("#notesCaret").hidden = true;
    for (const name of ["search", "first", "write"]) {
      if (stageEl(name).dataset.state === "active") stageEl(name).dataset.state = "pending";
    }
    setNotesBusy(false);
    refreshStats();
  }
}

$("#notesForm").addEventListener("submit", (event) => {
  event.preventDefault();
  if (notesUi.busy) { notesUi.controller.abort(); return; }
  const question = $("#notesInput").value.trim();
  if (question) askNotes(question);
});
$("#notesChips").replaceChildren(...NOTES_CHIPS.map((example) => {
  const chip = make("button", "chip", example);
  chip.type = "button";
  chip.addEventListener("click", () => { $("#notesInput").value = example; $("#notesForm").requestSubmit(); });
  return chip;
}));

// ====================== System: KPIs + charts ======================
function lowerIsBetter(value, good, warn) {
  if (value == null) return "none";
  return value <= good ? "good" : value <= warn ? "warn" : "bad";
}
function higherIsBetter(value, good, warn) {
  if (value == null) return "none";
  return value >= good ? "good" : value >= warn ? "warn" : "bad";
}
const STATUS_WORD = { good: "On target. ", warn: "Borderline. ", bad: "Needs work. ", neutral: "", none: "" };
const dash = (value, render) => (value == null ? { value: "—", unit: "" } : render(value));

// Har KPI: label, tooltip (Hinglish), aur read(stats) jo value/status/note deta hai.
const KPI_GROUPS = [
  {
    id: "assistant",
    title: "How is the assistant doing?",
    insight: assistantInsight,
    kpis: [
      {
        label: "Assistant replies",
        tip: ["Kya hai: is server ke chalne se ab tak assistant ne kitni baaton ka jawab diya.",
              "Kaise nikalta hai: Assistant tab ka har bheja hua message ek gina jata hai. New chat se ye nahi mitta.",
              "Neeche wali line: pichhle 1 minute mein kitne."],
        read: (s) => ({ value: String(s.assistant.turns), unit: "", status: "neutral", note: `${s.assistant.last_minute} in the last minute` }),
      },
      {
        label: "Average reply time",
        tip: ["Kya hai: message bhejne se poora jawab aane tak ka average time.",
              "Kaise nikalta hai: shortcut (bina model) aur model wale dono jawab milakar average.",
              "Achha kya hai: 2 second se kam. Model ka har call ~1 second leta hai."],
        read: (s) => ({ ...fmtMs(s.assistant.avg_ms), status: lowerIsBetter(s.assistant.avg_ms, 2000, 5000), note: "Target: under 2 s" }),
      },
      {
        label: "Instant replies",
        tip: ["Kya hai: kitne % jawab bina model ke, seedhe code se aaye (jaise 'walking ho gayi', 'habits dikhao').",
              "Kaise nikalta hai: shortcuts.py jo baatein pakka samajh leta hai, wo model tak jaati hi nahi.",
              "Kaise padho: zyada = tez aur sasta. Shak ho to shortcut nahi lagta, model ke paas jata hai."],
        read: (s) => ({ ...dash(s.assistant.shortcut_rate, (v) => ({ value: String(Math.round(v)), unit: "%" })), status: "neutral", note: "Answered without the model" }),
      },
      {
        label: "Model calls per reply",
        tip: ["Kya hai: ek jawab ke liye model ko average kitni baar bulana pada.",
              "Kaise nikalta hai: tool chunne ka call + (sirf notes ke liye) jawab likhne ka call. Confirmation code khud likhta hai.",
              "Achha kya hai: 1 ke aas-paas. 2 se upar = model galti karke dobara koshish kar raha hai."],
        read: (s) => ({ ...dash(s.assistant.avg_llm_calls, (v) => ({ value: v.toFixed(1), unit: "" })),
          status: lowerIsBetter(s.assistant.avg_llm_calls, 1.2, 2), note: "Target: about 1" }),
      },
      {
        label: "Tool eval",
        tip: ["Kya hai: 26 jaani-pehchaani Hinglish lines par kitni baar sahi tool + sahi arguments chale.",
              "Kaise nikalta hai: terminal mein python3 run_agent_eval.py (alag temporary database par, aapka data safe).",
              "Achha kya hai: 90% ya zyada. Prompt ya router badlo to dobara chalao."],
        read: (s) => {
          const e = s.agent_eval;
          if (!e) return { value: "—", unit: "", status: "none", note: "Run python3 run_agent_eval.py" };
          const pct = Math.round((100 * e.correct) / e.total);
          return { value: String(pct), unit: "%", status: higherIsBetter(pct, 90, 75), note: `${e.correct} of ${e.total} · avg ${seconds(e.avg_ms)}` };
        },
      },
    ],
  },
  {
    id: "speed",
    title: "Notes: how fast is it?",
    insight: speedInsight,
    kpis: [
      {
        label: "Average response",
        tip: ["Kya hai: sawal poochne se poora jawab khatam hone tak ka average time.",
              "Kaise nikalta hai: har sawal ka search + model ke likhne ka total time, phir sabka average.",
              "Achha kya hai: 3 second se kam. 8 second se upar dheema lagta hai."],
        read: (s) => ({ ...fmtMs(s.avg_total_ms), status: lowerIsBetter(s.avg_total_ms, 3000, 8000), note: "Target: under 3 s" }),
      },
      {
        label: "Slowest 5% (p95)",
        tip: ["Kya hai: 100 mein se 95 sawal is time ya usse jaldi hue. Yaani sabse dheeme sawalon ki limit.",
              "Kaise nikalta hai: sab response times chhote se bade lagao, 95% wale number par ruko. 20 se kam sawal hon to ye sabse dheeme sawal ke barabar hota hai.",
              "Achha kya hai: 6 second se kam. Average achha ho par ye bura ho to kuch sawal bahut atakte hain."],
        read: (s) => ({ ...fmtMs(s.p95_total_ms), status: lowerIsBetter(s.p95_total_ms, 6000, 15000), note: "Target: under 6 s" }),
      },
      {
        label: "First word",
        tip: ["Kya hai: sawal bhejne se pehla shabd screen par aane tak ka time. User ko 'tez' ya 'dheema' yahi lagta hai.",
              "Kaise nikalta hai: search time + model ko pehla token dene tak ka intezaar.",
              "Achha kya hai: 1.5 second se kam. Streaming ki wajah se poora jawab khatam hone ka intezaar nahi karna padta."],
        read: (s) => ({ ...fmtMs(s.avg_first_word_ms), status: lowerIsBetter(s.avg_first_word_ms, 1500, 4000), note: "Target: under 1.5 s" }),
      },
      {
        label: "Search",
        tip: ["Kya hai: aapke notes mein se milte-julte passages dhundhne ka time.",
              "Kaise nikalta hai: sawal ka embedding banana + har passage se cosine score nikalna. Vectors disk par cache hote hain.",
              "Achha kya hai: 0.5 second se kam. Files bahut badhengi to ye badhega."],
        read: (s) => ({ ...fmtMs(s.avg_search_ms), status: lowerIsBetter(s.avg_search_ms, 500, 1500), note: "Target: under 0.5 s" }),
      },
      {
        label: "Writing speed",
        tip: ["Kya hai: model ek second mein kitne tokens (shabdon ke tukde) likhta hai.",
              "Kaise nikalta hai: Ollama jo token count aur time batata hai, uska average.",
              "Achha kya hai: 20 ya zyada. Laptop ya model badalne par ye badalta hai."],
        read: (s) => ({ ...dash(s.avg_tokens_per_s, (v) => ({ value: String(Math.round(v)), unit: "tokens/s" })),
          status: higherIsBetter(s.avg_tokens_per_s, 20, 8), note: "Target: 20 or more" }),
      },
    ],
  },
  {
    id: "quality",
    title: "Notes: how good are the answers?",
    insight: qualityInsight,
    kpis: [
      {
        label: "Best-match score",
        tip: ["Kya hai: sawal aur sabse milte-julte passage ke beech ka cosine score (0 se 1). 1 ke paas matlab bahut milta-julta.",
              "Kaise nikalta hai: har sawal ke top passage ka score, phir average.",
              "Dhyan rakho: ye score akela nahi batata ki jawab notes mein hai ya nahi. Jo baat notes mein nahi hai, uska score bhi ooncha aa sakta hai."],
        read: (s) => ({ ...dash(s.avg_top_score, (v) => ({ value: v.toFixed(2), unit: "" })), status: higherIsBetter(s.avg_top_score, 0.6, 0.5), note: "Target: 0.60 or more" }),
      },
      {
        label: "“I don’t know” rate",
        tip: ["Kya hai: kitne % sawalon par model ne 'I don't know' bola.",
              "Kaise nikalta hai: jawab 'I don't know' se shuru hua to gina jata hai.",
              "Kaise padho: jo sawal notes mein nahi hain unpar 'I don't know' sahi hai. Jo notes mein hain unpar aaye to search ya prompt theek karo."],
        read: (s) => ({ ...dash(s.dont_know_rate, (v) => ({ value: String(Math.round(v)), unit: "%" })), status: "neutral", note: "Right when notes don't cover it" }),
      },
      {
        label: "Eval accuracy",
        tip: ["Kya hai: jaane-pehchane sawalon mein se kitne sahi aaye. Ye asli 'kitna sahi' hai.",
              "Kaise nikalta hai: python3 run_eval.py chalane par eval_results.json banti hai, ye usse padhta hai.",
              "Achha kya hai: 80% ya zyada."],
        read: (s) => {
          if (!s.eval) return { value: "—", unit: "", status: "none", note: "Run python3 run_eval.py" };
          const pct = Math.round((100 * s.eval.correct) / s.eval.total);
          return { value: String(pct), unit: "%", status: higherIsBetter(pct, 80, 60), note: `${s.eval.correct} of ${s.eval.total} correct` };
        },
      },
    ],
  },
  {
    id: "system",
    title: "Is everything running?",
    insight: null,
    kpis: [
      {
        label: "Notes indexed",
        tip: ["Kya hai: kitni files aur unke kitne tukde (passages) search ke liye taiyar hain.",
              "Kaise nikalta hai: my_data folder ki .txt aur .md files, har khali line par ek tukda.",
              "Nayi file daali ya badli to upar 'Reload notes' dabao."],
        read: (s) => ({ value: String(s.files), unit: s.files === 1 ? "file" : "files", status: s.chunks > 0 ? "good" : "bad", note: s.chunks > 0 ? `${s.chunks} passages` : "No notes loaded" }),
      },
      {
        label: "Voice (Whisper)",
        tip: ["Kya hai: offline awaaz-se-text. Recording isi Mac par whisper.cpp se text banti hai, internet nahi.",
              "Kaise nikalta hai: whisper-cli, ffmpeg aur poori model file (models/ggml-small.bin) teeno hon to Ready.",
              "Not ready ho to model download poora hone do, phir page refresh karo."],
        read: (s) => ({ value: s.whisper_ok ? "Ready" : "Not ready", unit: "", status: s.whisper_ok ? "good" : "warn", note: s.whisper_ok ? "Offline voice input on" : "Browser mic still works" }),
      },
      {
        label: "Uptime",
        tip: ["Kya hai: dashboard server ko chalte hue kitna time hua.",
              "Kaise nikalta hai: server shuru hone ke baad se ginta hai.",
              "Server restart karoge to ye aur sawalon ki ginti dono dobara 0 se shuru hongi."],
        read: (s) => ({ value: fmtUptime(s.uptime_s), unit: "", status: "neutral", note: s.warm ? "Model loaded in memory" : "Model loads on first use" }),
      },
    ],
  },
];

function assistantInsight(s) {
  const a = s.assistant;
  if (!a.turns) return "Assistant tab mein kuch bolo, yahan dikhega ki jawab kitna tez aur kaise aaya.";
  const instant = a.shortcut_rate == null ? 0 : Math.round(a.shortcut_rate);
  return `${instant}% replies came instantly from code. The rest used about ${a.avg_llm_calls ?? 0} model call each, because confirmations are written by code, not the model.`;
}

function speedInsight(s) {
  if (!s.questions_total) return "Notes tab mein sawal poocho, yahan dikhega ki time kahan jata hai.";
  const search = s.avg_search_ms, wait = s.avg_first_word_ms - s.avg_search_ms, write = s.avg_total_ms - s.avg_first_word_ms;
  const total = search + wait + write || 1;
  const stages = [["search", search], ["wait", wait], ["write", write]].sort((a, b) => b[1] - a[1]);
  const [name, ms] = stages[0];
  const pct = Math.round((100 * ms) / total);
  if (name === "write") return `${pct}% of the wait is the model writing the answer. Faster search would barely change it. Streaming helps because words appear early.`;
  if (name === "wait") return `${pct}% of the wait is the model getting started before the first word. Keeping it loaded in memory (already on) or a smaller model helps most.`;
  return `${pct}% of the wait is searching your notes. Passing fewer passages would help most.`;
}

function qualityInsight(s) {
  const answered = s.series.filter((d) => !d.dont_know).map((d) => d.top_score);
  const unknown = s.series.filter((d) => d.dont_know).map((d) => d.top_score);
  if (!answered.length && !unknown.length) return "Ask a few questions to see how scores behave.";
  if (answered.length && unknown.length && Math.max(...unknown) >= Math.min(...answered)) {
    return `An "I don't know" answer scored ${Math.max(...unknown).toFixed(2)}, higher than a real answer at ${Math.min(...answered).toFixed(2)}. A score cutoff alone can't tell them apart, so measure with an eval set.`;
  }
  return "So far the scores separate answered questions from unanswered ones. Keep checking as you add notes.";
}

const kpiRefs = [];
function buildGroups() {
  const host = $("#groups");
  for (const group of KPI_GROUPS) {
    const section = make("section", `panel group group-${group.id}`);
    const head = make("div", "group-head");
    head.append(make("h2", "", group.title));
    const insight = make("p", "group-insight");
    insight.hidden = !group.insight;
    head.append(insight);
    const grid = make("div", "kpis");
    for (const def of group.kpis) {
      const cell = make("div", "kpi");
      cell.tabIndex = 0;
      setTip(cell, def.label.replace(/[“”]/g, ""), def.tip);
      const label = make("div", "kpi-label");
      const info = make("span", "info", "i");
      info.setAttribute("aria-hidden", "true");
      label.append(make("span", "", def.label), info);
      const value = make("div", "kpi-value");
      const number = make("span", "num"), unit = make("span", "unit");
      value.append(number, unit);
      const note = make("div", "kpi-note");
      const dot = make("span", "dot"), word = make("span", "visually-hidden"), text = make("span");
      note.append(dot, word, text);
      cell.append(label, value, note);
      grid.append(cell);
      kpiRefs.push({ def, number, unit, dot, word, text });
    }
    section.append(head, grid);
    host.append(section);
    group.insightEl = insight;
  }
}

function updateKpis(stats) {
  for (const ref of kpiRefs) {
    const result = ref.def.read(stats);
    ref.number.textContent = result.value;
    ref.unit.textContent = result.unit;
    ref.dot.dataset.status = result.status;
    ref.word.textContent = STATUS_WORD[result.status] || "";
    ref.text.textContent = result.note;
  }
  for (const group of KPI_GROUPS) {
    if (group.insight) group.insightEl.textContent = group.insight(stats);
  }
}

const lastKey = {};
function changed(name, data) {
  const key = JSON.stringify(data);
  if (lastKey[name] === key) return false;
  lastKey[name] = key;
  return true;
}
const emptyChart = (text) => make("p", "empty", text);
function niceMax(valueSeconds) {
  return [1, 2, 4, 8, 12, 16, 20, 40, 60, 120, 300].find((n) => n >= valueSeconds) || Math.ceil(valueSeconds);
}

function drawAxes(svg, m, plotW, plotH, ticks, label) {
  for (const t of ticks) {
    const y = m.t + plotH - t.frac * plotH;
    svgEl("line", { class: "grid-line", x1: m.l, x2: m.l + plotW, y1: y, y2: y }, svg);
    const text = svgEl("text", { class: "axis-text", x: m.l - 8, y: y + 4, "text-anchor": "end" }, svg);
    text.textContent = label(t.value);
  }
}

function barChart(host, rows, ariaLabel) {
  // rows: [{ segments: [[className, ms], ...], tipTitle, tipLines }]
  host.replaceChildren();
  const W = 720, H = 230, m = { l: 46, r: 8, t: 12, b: 26 };
  const plotW = W - m.l - m.r, plotH = H - m.t - m.b;
  const totals = rows.map((r) => r.segments.reduce((sum, [, ms]) => sum + ms, 0));
  const yMax = niceMax(Math.max(...totals, 1) / 1000);
  const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": ariaLabel }, host);
  drawAxes(svg, m, plotW, plotH, [0, 1, 2, 3, 4].map((i) => ({ frac: i / 4, value: (yMax * i) / 4 })), (v) => (Number.isInteger(v) ? v : v.toFixed(1)) + " s");
  const slots = Math.max(rows.length, 12), slotW = plotW / slots, barW = Math.min(slotW * 0.64, 28);
  rows.forEach((row, i) => {
    const x = m.l + i * slotW + (slotW - barW) / 2;
    let bottom = m.t + plotH;
    for (const [cls, ms] of row.segments) {
      const h = Math.max((ms / 1000 / yMax) * plotH, ms > 0 ? 2 : 0);  // instant jawab bhi dikhe (2px)
      if (h <= 0) continue;
      svgEl("rect", { class: cls, x, y: bottom - h, width: barW, height: h, rx: 2 }, svg);
      bottom -= h;
    }
    const hit = svgEl("rect", { class: "hit", x: m.l + i * slotW, y: m.t, width: slotW, height: plotH }, svg);
    setTip(hit, row.tipTitle, row.tipLines);
  });
  const left = svgEl("text", { class: "axis-text", x: m.l, y: H - 6 }, svg); left.textContent = "oldest";
  const right = svgEl("text", { class: "axis-text", x: W - m.r, y: H - 6, "text-anchor": "end" }, svg); right.textContent = "latest";
}

function renderAssistantChart(series) {
  const host = $("#assistantChart");
  if (!series.length) { host.replaceChildren(emptyChart("Assistant tab mein kuch bolo, har jawab ka time yahan dikhega.")); return; }
  barChart(host, series.map((d) => ({
    segments: [[`bar-${d.route === "shortcut" ? "shortcut" : d.route === "chat" ? "chat" : "model"}`, d.ms]],
    tipTitle: shorten(d.text, 70),
    tipLines: [`Time: ${duration(d.ms)}`, `Raasta: ${ROUTE_TEXT[d.route] || d.route}`],
  })), `Reply time for the last ${series.length} assistant messages.`);
}

function renderTimeChart(series) {
  const host = $("#timeChart");
  if (!series.length) { host.replaceChildren(emptyChart("Notes tab mein sawal poocho, timing yahan dikhegi.")); return; }
  barChart(host, series.map((d) => ({
    segments: [["seg-search", d.search_ms], ["seg-wait", d.wait_ms], ["seg-write", d.write_ms]],
    tipTitle: shorten(d.question, 70),
    tipLines: [`Search: ${seconds(d.search_ms)}`, `Waiting for first word: ${seconds(d.wait_ms)}`, `Writing: ${seconds(d.write_ms)}`,
      `Total: ${seconds(d.search_ms + d.wait_ms + d.write_ms)}`],
  })), `Stacked bars of response time for the last ${series.length} notes questions. The table below has the same numbers.`);
}

function renderScoreChart(series) {
  const host = $("#scoreChart");
  host.replaceChildren();
  if (!series.length) { host.append(emptyChart("Ask a question to see match scores.")); return; }
  const W = 460, H = 230, m = { l: 36, r: 8, t: 12, b: 26 };
  const plotW = W - m.l - m.r, plotH = H - m.t - m.b;
  const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, role: "img",
    "aria-label": "Match score for each recent question. Filled dots were answered, rings were I don't know. The table has the same data." }, host);
  drawAxes(svg, m, plotW, plotH, [0, 1, 2, 3, 4].map((i) => ({ frac: i / 4, value: i / 4 })), (v) => v.toFixed(2).replace(/0$/, ""));
  const yFor = (score) => m.t + plotH - clamp(score, 0, 1) * plotH;
  svgEl("line", { class: "ref-line", x1: m.l, x2: m.l + plotW, y1: yFor(0.6), y2: yFor(0.6) }, svg);
  const label = svgEl("text", { class: "axis-text", x: m.l + plotW, y: yFor(0.6) - 5, "text-anchor": "end" }, svg);
  label.textContent = "target 0.60";
  const slots = Math.max(series.length, 12), slotW = plotW / slots;
  series.forEach((d, i) => {
    const cx = m.l + i * slotW + slotW / 2, cy = yFor(d.top_score);
    svgEl("circle", { class: d.dont_know ? "dot-idk" : "dot-ok", cx, cy, r: 5 }, svg);
    const hit = svgEl("circle", { class: "hit", cx, cy, r: 12 }, svg);
    setTip(hit, shorten(d.question, 70), [`Best match: ${d.top_score.toFixed(2)}`, d.dont_know ? "Result: I don't know" : "Result: answered"]);
  });
}

let topK = 5;
function renderFiles(files) {
  const host = $("#fileBars");
  host.replaceChildren();
  if (!files.length) { host.append(emptyChart("Files show up here once you ask questions.")); return; }
  const top = Math.max(...files.map((f) => f.count));
  for (const f of files) {
    const row = make("div", "filebar");
    row.tabIndex = 0;
    setTip(row, f.file, [`Kya hai: ye file ${f.count} baar top ${topK} passages mein aayi.`,
      "Kaise nikalta hai: har sawal ke liye jo passages model ko diye gaye, unmein is file ke kitne the, sab sawalon ka total."]);
    const line = make("div", "filebar-row");
    line.append(make("span", "name", f.file), make("span", "count", String(f.count)));
    const meter = make("div", "meter"), fill = make("span");
    fill.style.width = `${(100 * f.count) / top}%`;
    meter.append(fill);
    row.append(line, meter);
    host.append(row);
  }
}

function renderRecent(rows) {
  const body = $("#recentBody");
  body.replaceChildren();
  $("#recentEmpty").hidden = rows.length > 0;
  for (const r of rows) {
    const tr = make("tr");
    tr.append(make("td", "muted", clock(r.ts)));
    const q = make("td", "q", r.question);
    q.title = r.question;
    tr.append(q, make("td", "", r.top_file), make("td", "", r.top_score.toFixed(2)), make("td", "", seconds(r.total_ms)));
    const result = make("td");
    result.append(make("span", r.dont_know ? "badge idk" : "badge ok", r.dont_know ? "I don't know" : "Answered"));
    tr.append(result);
    body.append(tr);
  }
}

function renderSystem(stats, force = false) {
  updateKpis(stats);
  topK = stats.top_k;
  if (force) for (const key of Object.keys(lastKey)) delete lastKey[key];
  if (changed("assistant", stats.assistant.series)) renderAssistantChart(stats.assistant.series);
  if (changed("time", stats.series)) { renderTimeChart(stats.series); renderScoreChart(stats.series); }
  if (changed("files", stats.files_used)) renderFiles(stats.files_used);
  if (changed("recent", stats.recent)) renderRecent(stats.recent);
}

// ====================== Status pill + banner ======================
function renderEngine(stats) {
  $("#engine").dataset.ok = String(stats.ollama_ok);
  $("#engineText").textContent = stats.ollama_ok ? "Ollama ready" : "Ollama band hai";
  $("#engineModels").textContent = stats.chat_model;
  const banner = $("#banner");
  if (!stats.ollama_ok) banner.textContent = "Ollama se baat nahi ho rahi. Ollama app kholo; shortcuts (habit done, list) phir bhi chalte hain.";
  else if (stats.chunks === 0) banner.textContent = "Notes load nahi hain. my_data mein .md ya .txt files daalo, phir System tab mein Reload notes dabao.";
  banner.hidden = stats.ollama_ok && stats.chunks > 0;
}

let lastStats = null;
async function refreshStats() {
  try {
    const stats = await getJSON("/api/stats");
    lastStats = stats;
    renderEngine(stats);
    updateVoiceOptions(stats);
    if (currentView === "system") renderSystem(stats);
  } catch (error) {
    $("#engine").dataset.ok = "false";
    $("#engineText").textContent = "Server band hai";
  }
}

$("#reloadBtn").addEventListener("click", async () => {
  const button = $("#reloadBtn");
  button.disabled = true;
  try {
    const data = await postJSON("/api/reload", {});
    toast(`Reloaded ${plural(data.files, "file", "files")}, ${data.chunks} passages.`);
  } catch (error) {
    toast(error.status === 502 ? error.message : SERVER_DOWN, "error");
  }
  button.disabled = false;
  refreshStats();
});

// ====================== Settings + keyboard ======================
$("#speakToggle").checked = loadSetting("speak", "1") === "1";
$("#speakToggle").addEventListener("change", (event) => {
  saveSetting("speak", event.target.checked ? "1" : "0");
  if (!event.target.checked) stopSpeaking();
});
if ($("#ttsEngine")) {
  $("#ttsEngine").value = loadSetting("ttsEngine", "browser");
  $("#ttsEngine").addEventListener("change", (event) => {
    saveSetting("ttsEngine", event.target.value);
  });
}
$("#voiceEngine").value = loadSetting("voiceEngine", "whisper");
$("#voiceEngine").addEventListener("change", (event) => { saveSetting("voiceEngine", event.target.value); syncLangSelect(); });
$("#micLang").value = loadSetting("micLang", "en-IN");
$("#micLang").addEventListener("change", (event) => saveSetting("micLang", event.target.value));
if ("speechSynthesis" in window) speechSynthesis.getVoices();  // kuch browsers mein awaazein der se load hoti hain

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    if (closeOverlays()) return;
    hideTip(); stopSpeaking(); cancelAutoSend("Send cancelled.");
    if (voice.active) stopVoice();
  }
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") { event.preventDefault(); openPalette(); return; }
  const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName);
  const overlayOpen = !$("#palette").hidden || !$("#shortcuts").hidden;
  if (overlayOpen) return;  // dialog khula hai: peeche ke shortcuts ("/", "?") nahi
  if (event.key === "?" && !typing) { event.preventDefault(); openShortcuts(); return; }
  if (event.key === "/" && !typing && !event.metaKey && !event.ctrlKey) {
    event.preventDefault();
    if (currentView !== "assistant") showView("assistant");
    $("#chatInput").focus();
  }
});

// ====================== Command palette (⌘K) ======================
// Ek jagah se sab: tab badlo, nayi chat, awaaz, paani +1, theme, habit done. Kuch bhi likho to
// "assistant se poochho" ya "reminder jodo" bhi ban jata hai.
const palette = { items: [], index: 0, lastFocus: null };

function paletteCommands() {
  const go = (view, label, iconName) => ({ group: "Go to", label, icon: iconName, run: () => showView(view) });
  const commands = [
    go("assistant", "Assistant", "chat"), go("data", "My data", "layers"), go("notes", "Notes", "book"), go("system", "System", "chart"),
    { group: "Actions", label: "New chat", icon: "edit", run: () => $("#newChatBtn").click() },
    { group: "Actions", label: "Speak to the assistant", icon: "mic", run: () => { showView("assistant"); toggleVoice("chat"); } },
    { group: "Actions", label: "Add a glass of water", icon: "droplet", run: () => {
      const water = (overviewData && overviewData.health.find((h) => h.kind === "hydration")) || {};
      doAction({ action: "log_health", kind: "hydration", value: (water.today || 0) + 1 });
    } },
    { group: "Actions", label: "Toggle theme", icon: "auto", run: () => $("#themeBtn").click() },
    { group: "Actions", label: "Reload notes", icon: "refresh", run: () => $("#reloadBtn").click() },
    { group: "Actions", label: "Keyboard shortcuts", icon: "keyboard", hint: "?", run: () => openShortcuts() },
  ];
  for (const habit of ((overviewData && overviewData.habits) || []).filter((h) => !h.done_today)) {
    commands.push({ group: "Habits", label: `Mark “${habit.name}” done today`, icon: "check", run: () => doAction({ action: "check_in", habit: habit.name }) });
  }
  return commands;
}

function dataCommands(words) {
  // Saved data palette mein: overview pehle se browser ke paas hai, isliye ye search ~0 ms ki hai.
  if (!overviewData) return [];
  const hit = (text) => words.every((w) => text.toLowerCase().includes(w));
  const found = [];
  const add = (label, iconName, run) => found.push({ group: "Your data", label, icon: iconName, run });
  for (const item of overviewData.items || []) {
    if (hit(`${item.name} ${item.place}`)) add(`${item.name} — ${item.place}`, "pin", () => showView("data"));
  }
  for (const thing of (overviewData.things && overviewData.things.list) || []) {
    if (hit(`${thing.name} ${thing.category} ${thing.status || ""} ${thing.place || ""}`)) {
      add(`${thing.name} (${thing.category}${thing.place ? ` · ${thing.place}` : ""})`, "book", () => showView("data"));
    }
  }
  for (const person of overviewData.contacts || []) {
    if (hit(`${person.name} ${person.nicknames || ""} ${person.phone}`)) {
      add(`${person.name} — ${person.phone} (copy)`, "user", () => {
        navigator.clipboard && navigator.clipboard.writeText(person.phone).catch(() => {});
        toast(`${person.name} ka number copy ho gaya.`);
      });
    }
  }
  for (const task of (overviewData.tasks && overviewData.tasks.pending) || []) {
    if (hit(`${task.title} ${task.when || ""}`)) add(`${task.title}${task.when ? ` · ${task.when}` : ""}`, "check", () => showView("data"));
  }
  for (const goal of overviewData.goals || []) {
    if (hit(goal.title)) add(`${goal.title} · ${goal.days_left} din baaki`, "target", () => showView("data"));
  }
  return found.slice(0, 8);
}

function filterCommands(query) {
  const q = query.trim().toLowerCase();
  const all = paletteCommands();
  if (!q) return all;
  const words = q.split(/\s+/);
  const matches = all.filter((c) => words.every((w) => `${c.label} ${c.group}`.toLowerCase().includes(w)));
  return matches.concat(dataCommands(words), [
    { group: "Quick", label: `Ask the assistant: “${query.trim()}”`, icon: "sparkle", run: () => { showView("assistant"); sendChat(query.trim()); } },
    { group: "Quick", label: `Add reminder: “${query.trim()}”`, icon: "plus", run: () => quickAddTask(query.trim()) },
  ]);
}

function renderPalette() {
  const list = $("#paletteList");
  list.replaceChildren();
  palette.items = filterCommands($("#paletteInput").value);
  palette.index = Math.min(palette.index, Math.max(palette.items.length - 1, 0));
  if (!palette.items.length) { list.append(make("li", "palette-empty", "Nothing found")); return; }
  let group = null;
  palette.items.forEach((command, i) => {
    if (command.group !== group) {
      group = command.group;
      const heading = make("li", "palette-group", group);
      heading.setAttribute("role", "presentation");
      list.append(heading);
    }
    const item = make("li", "palette-item");
    item.id = `cmd-${i}`;
    item.setAttribute("role", "option");
    item.setAttribute("aria-selected", String(i === palette.index));
    item.append(icon(command.icon, 16), make("span", "", command.label));
    if (command.hint) { const hint = make("span", "hint"); hint.append(make("span", "kbd", command.hint)); item.append(hint); }
    item.addEventListener("mousemove", () => { if (palette.index !== i) { palette.index = i; highlightPalette(); } });
    item.addEventListener("click", () => runPalette(i));
    list.append(item);
  });
  $("#paletteInput").setAttribute("aria-activedescendant", `cmd-${palette.index}`);
}

function highlightPalette() {
  for (const item of $$(".palette-item")) item.setAttribute("aria-selected", String(item.id === `cmd-${palette.index}`));
  const active = $(`#cmd-${palette.index}`);
  if (active) active.scrollIntoView({ block: "nearest" });
  $("#paletteInput").setAttribute("aria-activedescendant", `cmd-${palette.index}`);
}

function openPalette() {
  $("#shortcuts").hidden = true;
  if ($("#palette").hidden) palette.lastFocus = document.activeElement;
  $("#palette").hidden = false;
  $("#paletteInput").value = "";
  palette.index = 0;
  renderPalette();
  $("#paletteInput").focus();
}

function closePalette() {
  $("#palette").hidden = true;
  if (palette.lastFocus && palette.lastFocus.focus) palette.lastFocus.focus();
}

function runPalette(i) {
  const command = palette.items[i];
  const returnTo = palette.lastFocus;
  closePalette();
  if (command) command.run();
  if (!$("#shortcuts").hidden) shortcutsReturnFocus = returnTo;  // palette se shortcuts khola: band hone par wahin wapas
}

$("#paletteInput").addEventListener("input", () => { palette.index = 0; renderPalette(); });
$("#paletteInput").addEventListener("keydown", (event) => {
  const count = Math.max(palette.items.length, 1);
  if (event.key === "ArrowDown") { event.preventDefault(); palette.index = (palette.index + 1) % count; highlightPalette(); }
  else if (event.key === "ArrowUp") { event.preventDefault(); palette.index = (palette.index - 1 + count) % count; highlightPalette(); }
  else if (event.key === "Enter") { event.preventDefault(); runPalette(palette.index); }
});
$("#palette").addEventListener("mousedown", (event) => { if (event.target === $("#palette")) closePalette(); });
$("#paletteBtn").addEventListener("click", openPalette);

// ====================== Keyboard shortcuts (?) ======================
let shortcutsReturnFocus = null;

function openShortcuts() {
  const fromPalette = !$("#palette").hidden;
  shortcutsReturnFocus = fromPalette ? palette.lastFocus : document.activeElement;
  $("#palette").hidden = true;
  $("#shortcuts").hidden = false;
  $("#shortcutsClose").focus();
}

function closeShortcuts() {
  $("#shortcuts").hidden = true;
  if (shortcutsReturnFocus && shortcutsReturnFocus.focus) shortcutsReturnFocus.focus();  // jahan the wahin wapas
  shortcutsReturnFocus = null;
}

function closeOverlays() {
  let closed = false;
  if (!$("#palette").hidden) { closePalette(); closed = true; }
  if (!$("#shortcuts").hidden) { closeShortcuts(); closed = true; }
  return closed;
}

$("#shortcutsClose").addEventListener("click", closeShortcuts);
$("#shortcuts").addEventListener("mousedown", (event) => { if (event.target === $("#shortcuts")) closeShortcuts(); });

// ====================== Cards: band/khol (yaad rehta hai) + quick add ======================
function setupCollapsibles() {
  let state = {};
  try { state = JSON.parse(loadSetting("collapsed", "{}")) || {}; } catch (error) { state = {}; }
  for (const card of $$("[data-card]")) {
    const key = card.dataset.card;
    const button = $(".collapse-btn", card);
    const apply = (collapsed) => {
      card.dataset.collapsed = String(collapsed);
      button.setAttribute("aria-expanded", String(!collapsed));
    };
    apply(Boolean(state[key]));
    button.addEventListener("click", () => {
      const next = card.dataset.collapsed !== "true";
      apply(next);
      state[key] = next;
      saveSetting("collapsed", JSON.stringify(state));
    });
  }
}

async function quickAddTask(text, input) {
  text = text.trim();
  if (!text) return;
  if (input) input.disabled = true;
  const ok = await doAction({ action: "add_task", text });  // samay code se samjha jata hai ("kal 6 baje"), model nahi
  if (input) { input.disabled = false; if (ok) input.value = ""; input.focus(); }  // fail hua to likha text rehne do
}

$("#quickTaskForm").addEventListener("submit", (event) => { event.preventDefault(); quickAddTask($("#quickTaskInput").value, $("#quickTaskInput")); });
$("#dataTaskForm").addEventListener("submit", (event) => { event.preventDefault(); quickAddTask($("#dataTaskInput").value, $("#dataTaskInput")); });
$("#habitAddForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = $("#habitAddInput");
  const name = input.value.trim();
  if (!name) return;
  input.disabled = true;
  const ok = await doAction({ action: "add_habit", name });
  input.disabled = false;
  if (ok) input.value = "";
  input.focus();
});

// ====================== Start ======================
hydrateIcons();
applyTheme(theme);
setMicState($("#micBtn"), "idle");
setMicState($("#notesMic"), "idle");
$("#sendBtn").disabled = true;
buildGroups();
setupCollapsibles();
renderSuggestions();
showView((location.hash || "").slice(1) || loadSetting("view", "assistant"));
loadChatHistory();
refreshStats();
let lastStatsAt = 0;
setInterval(() => {
  if (document.visibilityState !== "visible") return;
  const every = currentView === "system" ? 5000 : 15000;  // System tab par live, baaki jagah sirf status pill
  if (performance.now() - lastStatsAt >= every - 100) { lastStatsAt = performance.now(); refreshStats(); }
}, 5000);
setInterval(() => { if (document.visibilityState === "visible" && (currentView === "assistant" || currentView === "data")) refreshOverview(); }, 30000);
