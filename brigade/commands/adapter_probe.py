import json

from brigade.command import Command
from brigade.runtime import Runtime
from brigade.system.ask_client import ClientQuestion
from brigade.system.ask_configured_client import ask_configured_client
from brigade.system.read_configured_client_name import read_configured_client_name

OPERATION = "probe"
PROBE_REQUEST = {"schema_version": 1}
TEXT_INDENT = 2


def _read_request(options):
    return options


def _render_text(document: dict) -> str:
    return json.dumps(document, indent=TEXT_INDENT)


def _decide_exit_code(document: dict) -> int:
    return 0


def adapter_probe(request, runtime: Runtime) -> dict:
    client_name = read_configured_client_name(runtime)
    client = runtime.resolve_plugin("client", client_name)
    return ask_configured_client(client, ClientQuestion(client_name, OPERATION, PROBE_REQUEST), runtime)


COMMAND = Command(
    path=("adapter", OPERATION),
    help=f"answer {OPERATION}, the request read on stdin",
    group_help="answer one operation of the configured client adapter, or print the matrix of every adapter",
    run=adapter_probe,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
