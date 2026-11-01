const POLL_INTERVAL_MS = 5000;
const FIRST_VIEW = "status";
const TOKEN_HEADER = "X-Brigade-Token";

function selectView() {
  return window.location.hash.slice(1) || FIRST_VIEW;
}

function readToken() {
  return document.querySelector('meta[name="brigade-token"]').content;
}

async function showView() {
  if (document.visibilityState !== "visible") {
    return;
  }
  const response = await fetch(`/views/${selectView()}`);
  document.getElementById("view").innerHTML = await response.text();
}

async function postAction(event) {
  const button = event.target.closest("button[data-post]");
  if (button === null) {
    return;
  }
  const response = await fetch(button.dataset.post, { method: "POST", headers: { [TOKEN_HEADER]: readToken() } });
  if (!response.ok) {
    window.alert((await response.json()).error);
  }
  await showView();
}

function pollView() {
  if (document.activeElement && document.activeElement.form) {
    return;
  }
  showView();
}

function submitView(event) {
  event.preventDefault();
  window.location.hash = `${event.target.dataset.view}?${new URLSearchParams(new FormData(event.target))}`;
}

window.addEventListener("hashchange", showView);
document.addEventListener("visibilitychange", showView);
document.addEventListener("click", postAction);
document.addEventListener("submit", submitView);
window.setInterval(pollView, POLL_INTERVAL_MS);
showView();
