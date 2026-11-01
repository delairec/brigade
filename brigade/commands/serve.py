import argparse
import secrets
import sys

from brigade.command import Argument, Command
from brigade.dashboard.choose_dashboard_port import choose_dashboard_port
from brigade.dashboard.start_dashboard import start_dashboard
from brigade.runtime import Runtime
from brigade.system.read_configuration import CONFIGURATION_OPTIONAL, read_configuration

DOCUMENT_SCHEMA_VERSION = 1
TOKEN_BYTES = 32
POLL_INTERVAL_S = 60.0
NOT_DONE = False


class _UrlAnnouncer:
    def __init__(self, url: str):
        self.url = url
        self.announced = False

    def poll(self) -> bool:
        if not self.announced:
            sys.stdout.write(f"{self.url}\n")
            sys.stdout.flush()
            self.announced = True
        return NOT_DONE


def _render_text(document: dict) -> str:
    return f"stopped serving {document['url']}"


def serve(request: argparse.Namespace, runtime: Runtime) -> dict:
    port = choose_dashboard_port(request.port, read_configuration(runtime, CONFIGURATION_OPTIONAL))
    with start_dashboard(port, secrets.token_urlsafe(TOKEN_BYTES), runtime) as dashboard:
        runtime.poll_until_signalled(_UrlAnnouncer(dashboard.url).poll, POLL_INTERVAL_S)
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, "url": dashboard.url}


COMMAND = Command(
    path=("serve",),
    help="serve the dashboard on the loopback address until SIGINT or SIGTERM",
    arguments=(
        Argument(("--port",), {"type": int, "help": "the port to listen on, by default dashboard_port of config.toml"}),
    ),
    run=serve,
    render_text=_render_text,
)
