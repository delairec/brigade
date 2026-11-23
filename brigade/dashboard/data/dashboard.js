const POLL_INTERVAL_MS = Number(document.querySelector('meta[name="brigade-poll-interval-ms"]').content);
const FIRST_VIEW = "status";
const TOKEN_HEADER = "X-Brigade-Token";
const HEARTBEAT_REGION = "/views/heartbeat";
const RAIL_REGION = "/views/rail";
const PROJECT_PARAMETER = "project";
const BUSY_DELAY_MS = 300;
const pendingPosts = new Set();
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

async function waitVisibly(element, wait) {
  const shown = window.setTimeout(() => element.setAttribute("aria-busy", "true"), BUSY_DELAY_MS);
  try {
    return await wait;
  } finally {
    window.clearTimeout(shown);
    element.removeAttribute("aria-busy");
  }
}

function markPendingPosts() {
  for (const button of document.querySelectorAll("button[data-post]")) {
    button.disabled = pendingPosts.has(button.dataset.post);
  }
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
  markPendingPosts();
  for (const summary of region.querySelectorAll("details > summary")) {
    if (shownSummaries.has(summary.textContent)) {
      summary.parentElement.open = openSummaries.has(summary.textContent);
    }
  }
  restoreFocus(region, focusedName);
}

async function showRegion(region, path) {
  try {
    const response = await fetch(addProject(path));
    swapFragment(region, await response.text());
  } catch {
    showNotice(`The dashboard server did not answer ${path}.`);
  }
}

function readNextTick() {
  const region = document.querySelector("[data-next-tick]");
  return showRegion(region, region.dataset.nextTick);
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

function readFirstSegment(address) {
  return address.split(/[/?]/)[0];
}

function markCurrentView() {
  const current = readFirstSegment(selectView());
  for (const link of document.querySelectorAll("[data-rail-view]")) {
    if (link.dataset.railView === current) {
      link.setAttribute("aria-current", "page");
    } else {
      link.removeAttribute("aria-current");
    }
  }
}

function stampReadTime(region) {
  const fresh = region.querySelector("[data-fresh]");
  if (fresh !== null) {
    fresh.dataset.refreshes ??= fresh.textContent;
    const readAt = new Date().toISOString().slice(11, 19);
    fresh.textContent = `read ${readAt}Z · ${fresh.dataset.refreshes}`;
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

async function refreshNextTick(event) {
  const button = event.target.closest("[data-refresh-next-tick]");
  if (button === null) {
    return;
  }
  button.disabled = true;
  await waitVisibly(button.closest(".next-tick"), readNextTick());
  button.disabled = false;
}

function showRegions() {
  if (document.visibilityState !== "visible") {
    return Promise.resolve();
  }
  document.querySelector(".next-tick").hidden = selectView() !== FIRST_VIEW;
  const shown = showView(document.getElementById("view"), `/views/${selectView()}`);
  for (const region of document.querySelectorAll("[data-region]")) {
    selectRegionShow(region.dataset.region)(region, region.dataset.region);
  }
  return shown;
}

function showChosenView() {
  return waitVisibly(document.getElementById("view"), showRegions());
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
  await waitVisibly(document.getElementById("view"), sendPost(button.dataset.post));
}

async function sendPost(address) {
  pendingPosts.add(address);
  markPendingPosts();
  try {
    const response = await fetch(address, { method: "POST", headers: { [TOKEN_HEADER]: readToken() } });
    showNotice(response.ok ? "" : (await response.json()).error);
    await showRegions();
  } catch {
    showNotice(`The dashboard server did not answer ${address}.`);
  } finally {
    pendingPosts.delete(address);
    markPendingPosts();
  }
}

function pollRegions() {
  if (document.activeElement?.closest("[data-pauses-poll]")) {
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
  const select = event.target.closest("select");
  if (!select) {
    return;
  }
  const leadsTo = select.selectedOptions[0]?.dataset.href;
  if (leadsTo !== undefined) {
    window.location.hash = leadsTo;
  } else if (select.form?.classList.contains("project-selector")) {
    select.form.requestSubmit();
  }
}

function submitRanges(event) {
  const form = event.target.closest("form[data-ranges]");
  if (form === null || event.target.type !== "date" || !form.checkValidity()) {
    return;
  }
  const day = (name) => form.elements[name].value;
  window.location.hash = `ledger?range=${day("before-start")}..${day("before-end")}&range=${day("after-start")}..${day("after-end")}`;
}

window.addEventListener("hashchange", showChosenView);
window.addEventListener("hashchange", markCurrentView);
document.addEventListener("visibilitychange", showRegions);
document.addEventListener("click", postAction);
document.addEventListener("click", refreshNextTick);
document.addEventListener("submit", submitView);
document.addEventListener("change", applySelection);
document.addEventListener("change", submitRanges);
window.setInterval(pollRegions, POLL_INTERVAL_MS);
showRegions();
readNextTick();
