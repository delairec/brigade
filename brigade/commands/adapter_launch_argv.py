import json
import sys

from brigade.command import Command
from brigade.runtime import Runtime
from brigade.system.ask_client import ClientQuestion
from brigade.system.ask_named_client import ask_named_client
from brigade.system.read_client_request import read_client_request
from brigade.system.read_configured_client import read_configured_client

OPERATION = "launch-argv"
TEXT_INDENT = 2


def _read_request(options) -> str:
    return sys.stdin.read()


def _render_text(document: dict) -> str:
    return json.dumps(document, indent=TEXT_INDENT)


def _decide_exit_code(document: dict) -> int:
    return 0


def adapter_launch_argv(request, runtime: Runtime) -> dict:
    client_request = read_client_request(OPERATION, request)
    configured = read_configured_client(runtime)
    client = runtime.resolve_plugin("client", configured.name)
    return ask_named_client(
        client, ClientQuestion(configured.name, OPERATION, client_request), configured.configuration, runtime
    )


COMMAND = Command(
    path=("adapter", OPERATION),
    help=f"answer {OPERATION}, the request read on stdin",
    group_help="answer one operation of the configured client adapter, or print the matrix of every adapter",
    run=adapter_launch_argv,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
