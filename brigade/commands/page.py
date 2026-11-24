import argparse
import json
from dataclasses import dataclass

from brigade.command import Argument, Command
from brigade.dashboard.answer_dashboard_request import answer_dashboard_request
from brigade.dashboard.dashboard_exchange import LOOPBACK_HOST, Dashboard, DashboardResponse, IncomingRequest
from brigade.dashboard.render_dashboard_page import render_dashboard_page
from brigade.dashboard.start_awawa_addon import start_awawa_addon
from brigade.errors import BrigadeError
from brigade.runtime import Runtime

DOCUMENT_SCHEMA_VERSION = 1
IN_PROCESS_PORT = 0
NO_TOKEN = ""
READING_METHOD = "GET"
OK = 200
VIEWS_PREFIX = "/views/"
AWAWA_PAGE = "awawa"


@dataclass(frozen=True)
class _Detail:
    listing: str
    collection: str
    identifier: str
    newest_by: str
    view: str


LISTED_PAGES = {
    "home": "status",
    "waves": "waves",
    "runs": "runs",
    "ledger": "ledger",
    "inbox": "inbox",
    "reports": "reports",
}
DETAIL_PAGES = {
    "wave": _Detail("/api/waves", "waves", "wave", "started_at", "waves"),
    "run": _Detail("/api/runs", "runs", "run", "started_at", "runs"),
    "report": _Detail("/api/reports", "reports", "id", "reported_at", "reports"),
}
PAGES = ("home", "waves", "wave", "runs", "run", "ledger", "inbox", "reports", "report", AWAWA_PAGE)


def _render_text(document: dict) -> str:
    return document["html"]


def _select(target: str, project: str | None) -> str:
    if project is None:
        return target
    return f"{target}?project={project}"


def _address(page: str, project: str | None, ask) -> str:
    if page in LISTED_PAGES:
        return LISTED_PAGES[page]
    if page == AWAWA_PAGE:
        if project is None:
            raise BrigadeError("the page awawa shows the corpus of one project: name it")
        return f"awawa/{project}"
    detail = DETAIL_PAGES[page]
    entries = json.loads(ask(_select(detail.listing, project)))[detail.collection]
    if not entries:
        raise BrigadeError(f"the page {page} shows one of none: brigade lists none")
    newest = max(entries, key=lambda entry: entry[detail.newest_by] or "")
    return f"{detail.view}/{newest[detail.identifier]}"


def page(request: argparse.Namespace, runtime: Runtime) -> dict:
    if request.page not in PAGES:
        raise BrigadeError(f"no page {request.page}; the pages are {', '.join(PAGES)}")
    with start_awawa_addon(runtime) as addon:
        dashboard = Dashboard(port=IN_PROCESS_PORT, token=NO_TOKEN, addon=addon)

        def respond(target: str) -> DashboardResponse:
            incoming = IncomingRequest(method=READING_METHOD, target=target, host=f"{LOOPBACK_HOST}:{IN_PROCESS_PORT}")
            return answer_dashboard_request(incoming, dashboard, runtime)

        def ask(target: str) -> str:
            response = respond(target)
            if response.status != OK:
                raise BrigadeError(f"{target} answered {response.status}: {response.body.decode()}")
            return response.body.decode()

        view = _select(f"{VIEWS_PREFIX}{_address(request.page, request.project, ask)}", request.project)

        def answer(target: str) -> str:
            return ask(target) if target == view else respond(_select(target, request.project)).body.decode()

        html = render_dashboard_page(request.page, view, answer)
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, "page": request.page, "html": html}


COMMAND = Command(
    path=("page",),
    help="print one page of the dashboard as a standalone HTML document, its stylesheet inline and its regions filled",
    arguments=(
        Argument(("page",), {"help": f"the page, one of {', '.join(PAGES)}"}),
        Argument(("--project",), {"help": "the project the page shows, every project by default"}),
    ),
    run=page,
    render_text=_render_text,
)
