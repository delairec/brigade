const POLL_INTERVAL_MS = 5000;
const FIRST_VIEW = "waves";

function selectView() {
  return window.location.hash.slice(1) || FIRST_VIEW;
}

async function showView() {
  if (document.visibilityState !== "visible") {
    return;
  }
  const response = await fetch(`/views/${selectView()}`);
  document.getElementById("view").innerHTML = await response.text();
}

window.addEventListener("hashchange", showView);
document.addEventListener("visibilitychange", showView);
window.setInterval(showView, POLL_INTERVAL_MS);
showView();
