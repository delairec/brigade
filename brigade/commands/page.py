import argparse

from brigade.command import Argument, Command
from brigade.dashboard.answer_dashboard_request import answer_dashboard_request
from brigade.dashboard.dashboard_exchange import LOOPBACK_HOST, Dashboard, IncomingRequest
from brigade.dashboard.render_dashboard_page import render_dashboard_page
from brigade.runtime import Runtime

DOCUMENT_SCHEMA_VERSION = 1
IN_PROCESS_PORT = 0
NO_TOKEN = ""
READING_METHOD = "GET"


class _NoAddon:
    def list_projects(self) -> frozenset[str]:
        return frozenset()


def _render_text(document: dict) -> str:
    return document["html"]


def page(request: argparse.Namespace, runtime: Runtime) -> dict:
    dashboard = Dashboard(port=IN_PROCESS_PORT, token=NO_TOKEN, addon=_NoAddon())

    def answer(target: str) -> str:
        incoming = IncomingRequest(method=READING_METHOD, target=target, host=f"{LOOPBACK_HOST}:{IN_PROCESS_PORT}")
        return answer_dashboard_request(incoming, dashboard, runtime).body.decode()

    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "page": request.page,
        "html": render_dashboard_page(request.page, answer),
    }


COMMAND = Command(
    path=("page",),
    help="print one page of the dashboard as a standalone HTML document, its stylesheet inline and its regions filled",
    arguments=(Argument(("page",), {"help": "the page, home, waves, runs, inbox, ledger or reports"}),),
    run=page,
    render_text=_render_text,
)
