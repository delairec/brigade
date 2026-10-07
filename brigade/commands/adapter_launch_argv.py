import json
import sys

from brigade.command import Command
from brigade.runtime import Runtime
from brigade.system.ask_client import ClientQuestion
from brigade.system.ask_configured_client import ask_configured_client
from brigade.system.read_client_request import read_client_request
from brigade.system.read_configured_client_name import read_configured_client_name

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
    client_name = read_configured_client_name(runtime)
    client = runtime.resolve_plugin("client", client_name)
    return ask_configured_client(client, ClientQuestion(client_name, OPERATION, client_request), runtime)


COMMAND = Command(
    path=("adapter", OPERATION),
    help=f"answer {OPERATION}, the request read on stdin",
    group_help="answer one operation of the configured client adapter, or print the matrix of every adapter",
    run=adapter_launch_argv,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
