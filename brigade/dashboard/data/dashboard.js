const POLL_INTERVAL_MS = 5000;
const FIRST_VIEW = "status";
const TOKEN_HEADER = "X-Brigade-Token";
const HEARTBEAT_REGION = "/views/heartbeat";
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
  showRegion(document.getElementById("view"), `/views/${selectView()}`);
  for (const region of document.querySelectorAll("[data-region]")) {
    const show = region.dataset.region === HEARTBEAT_REGION ? showHeartbeat : showRegion;
    show(region, region.dataset.region);
  }
}

function showNotice(message) {
  const notice = document.getElementById("notice");
  notice.textContent = message;
  notice.hidden = message === "";
}

async function postAction(event) {
  const button = event.target.closest("button[data-post]");
  if (button === null) {
    return;
  }
  const response = await fetch(button.dataset.post, { method: "POST", headers: { [TOKEN_HEADER]: readToken() } });
  showNotice(response.ok ? "" : (await response.json()).error);
  showRegions();
}

function pollRegions() {
  if (document.activeElement && document.activeElement.form) {
    return;
  }
  showRegions();
}

function submitView(event) {
  if (event.target.dataset.view === undefined) {
    return;
  }
  event.preventDefault();
  window.location.hash = `${event.target.dataset.view}?${new URLSearchParams(new FormData(event.target))}`;
}

window.addEventListener("hashchange", showRegions);
document.addEventListener("visibilitychange", showRegions);
document.addEventListener("click", postAction);
document.addEventListener("click", refreshNextTick);
document.addEventListener("submit", submitView);
window.setInterval(pollRegions, POLL_INTERVAL_MS);
showRegions();
readNextTick();
