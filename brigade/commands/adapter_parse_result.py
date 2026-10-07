import json
import sys

from brigade.command import Command
from brigade.system.ask_configured_client import ask_configured_client
from brigade.system.read_client_request import read_client_request

OPERATION = "parse-result"
TEXT_INDENT = 2


def _read_request(options) -> str:
    return sys.stdin.read()


def _render_text(document: dict) -> str:
    return json.dumps(document, indent=TEXT_INDENT)


def _decide_exit_code(document: dict) -> int:
    return 0


def adapter_parse_result(request, runtime) -> dict:
    return ask_configured_client(runtime, OPERATION, read_client_request(OPERATION, request)).document


COMMAND = Command(
    path=("adapter", OPERATION),
    help=f"answer {OPERATION}, the request read on stdin",
    group_help="answer one operation of the configured client adapter, or print the matrix of every adapter",
    run=adapter_parse_result,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
