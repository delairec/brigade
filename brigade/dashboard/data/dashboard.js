const POLL_INTERVAL_MS = 5000;
const FIRST_VIEW = "status";
const TOKEN_HEADER = "X-Brigade-Token";
const HEARTBEAT_REGION = "/views/heartbeat";
const RAIL_REGION = "/views/rail";
const MILLISECONDS_PER_SECOND = 1000;
const PROJECT_PARAMETER = "project";
const shownFragments = new Map();
const HEARTBEAT_UNREAD = Symbol("heartbeat unread");
let lastTickSeen = HEARTBEAT_UNREAD;

function selectView() {
  return window.location.hash.slice(1) || FIRST_VIEW;
}

function readToken() {
  return document.querySelector('meta[name="brigade-token"]').content;
}

function addProject(path) {
  const address = new URL(path, window.location.origin);
  const project = new URLSearchParams(window.location.search).get(PROJECT_PARAMETER);
  if (project) {
    address.searchParams.set(PROJECT_PARAMETER, project);
  }
  return address;
}

function readOpenSummaries(region) {
  return new Set(Array.from(region.querySelectorAll("details[open] > summary"), (summary) => summary.textContent));
}

function readShownSummaries(region) {
  return new Set(Array.from(region.querySelectorAll("details > summary"), (summary) => summary.textContent));
}

function readFocusedName(region) {
  const focused = document.activeElement;
  if (focused === null || !region.contains(focused)) {
    return "";
  }
  return focused.id || focused.name || "";
}

function restoreFocus(region, name) {
  if (name === "") {
    return;
  }
  const target = region.querySelector(`#${CSS.escape(name)}, [name="${CSS.escape(name)}"]`);
  if (target !== null) {
    target.focus();
  }
}

function swapFragment(region, fragment) {
  if (shownFragments.get(region) === fragment) {
    return;
  }
  const openSummaries = readOpenSummaries(region);
  const shownSummaries = readShownSummaries(region);
  const focusedName = readFocusedName(region);
  region.innerHTML = fragment;
  shownFragments.set(region, fragment);
  for (const summary of region.querySelectorAll("details > summary")) {
    if (shownSummaries.has(summary.textContent)) {
      summary.parentElement.open = openSummaries.has(summary.textContent);
    }
  }
  restoreFocus(region, focusedName);
}

async function showRegion(region, path) {
  const response = await fetch(addProject(path));
  swapFragment(region, await response.text());
}

function readNextTick() {
  const region = document.querySelector("[data-next-tick]");
  showRegion(region, region.dataset.nextTick);
}

function followTheTick(region) {
  const tick = region.querySelector("time");
  const seen = tick === null ? null : tick.dateTime;
  if (lastTickSeen !== HEARTBEAT_UNREAD && seen !== lastTickSeen) {
    readNextTick();
  }
  lastTickSeen = seen;
}

async function showHeartbeat(region, path) {
  await showRegion(region, path);
  followTheTick(region);
}

function markCurrentView() {
  const current = `#${selectView().split(/[/?]/)[0]}`;
  for (const link of document.querySelectorAll(".rail-group a")) {
    if (link.getAttribute("href") === current) {
      link.setAttribute("aria-current", "page");
    } else {
      link.removeAttribute("aria-current");
    }
  }
}

function stampReadTime(region) {
  const fresh = region.querySelector("[data-fresh]");
  if (fresh !== null) {
    const readAt = new Date().toISOString().slice(11, 19);
    fresh.textContent = `read ${readAt}Z · refreshes every ${POLL_INTERVAL_MS / MILLISECONDS_PER_SECOND} s`;
  }
}

async function showView(region, path) {
  await showRegion(region, path);
  stampReadTime(region);
  markCurrentView();
}

async function showRail(region, path) {
  await showRegion(region, path);
  markCurrentView();
}

function selectRegionShow(path) {
  if (path === HEARTBEAT_REGION) {
    return showHeartbeat;
  }
  if (path === RAIL_REGION) {
    return showRail;
  }
  return showRegion;
}

function refreshNextTick(event) {
  if (event.target.closest("[data-refresh-next-tick]") !== null) {
    readNextTick();
  }
}

function showRegions() {
  if (document.visibilityState !== "visible") {
    return;
  }
  document.querySelector(".next-tick").hidden = selectView() !== FIRST_VIEW;
  showView(document.getElementById("view"), `/views/${selectView()}`);
  for (const region of document.querySelectorAll("[data-region]")) {
    selectRegionShow(region.dataset.region)(region, region.dataset.region);
  }
}

function showNotice(message) {
  const notice = document.getElementById("notice");
  notice.textContent = message;
  notice.hidden = message === "";
}

function readActionAddress(button) {
  const name = button.dataset.with;
  if (name === undefined) {
    return button.dataset.post;
  }
  const select = button.parentElement.querySelector(`select[name="${CSS.escape(name)}"]`);
  const separator = button.dataset.post.includes("?") ? "&" : "?";
  return `${button.dataset.post}${separator}${encodeURIComponent(name)}=${encodeURIComponent(select.value)}`;
}

async function postAction(event) {
  const button = event.target.closest("button[data-post]");
  if (button === null) {
    return;
  }
  const response = await fetch(readActionAddress(button), { method: "POST", headers: { [TOKEN_HEADER]: readToken() } });
  showNotice(response.ok ? "" : (await response.json()).error);
  showRegions();
}

function pollRegions() {
  if (document.activeElement && document.activeElement.form) {
    return;
  }
  showRegions();
}

function readViewAddress(form) {
  return `${form.dataset.view}?${new URLSearchParams(new FormData(form))}`;
}

function submitView(event) {
  if (event.target.dataset.view === undefined) {
    return;
  }
  event.preventDefault();
  window.location.hash = readViewAddress(event.target);
}

function applySelection(event) {
  const form = event.target.closest("select")?.form;
  if (!form) {
    return;
  }
  if (form.dataset.view !== undefined) {
    window.location.hash = readViewAddress(form);
  } else if (form.classList.contains("project-selector")) {
    form.requestSubmit();
  }
}

window.addEventListener("hashchange", showRegions);
window.addEventListener("hashchange", markCurrentView);
document.addEventListener("visibilitychange", showRegions);
document.addEventListener("click", postAction);
document.addEventListener("click", refreshNextTick);
document.addEventListener("submit", submitView);
document.addEventListener("change", applySelection);
window.setInterval(pollRegions, POLL_INTERVAL_MS);
showRegions();
readNextTick();
