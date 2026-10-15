import json
from operator import attrgetter

from brigade.command import Command
from brigade.runtime import Runtime
from brigade.system.ask_configured_client import ConfiguredClientAnswer, ask_configured_client
from brigade.system.describe_configured_client_answer import describe_configured_client_answer
from brigade.system.probe_request import ProbeRequest
from brigade.system.read_configured_client import read_configured_client

OPERATION = "probe"
TEXT_INDENT = 2


def _read_request(options):
    return options


def _render_text(document: dict) -> str:
    return json.dumps(document, indent=TEXT_INDENT)


def _decide_exit_code(document: dict) -> int:
    return 0


def adapter_probe(request, runtime: Runtime) -> ConfiguredClientAnswer:
    configured = read_configured_client(runtime)
    client = runtime.resolve_plugin("client", configured.name)
    return ask_configured_client(client, configured, ProbeRequest(), runtime)


COMMAND = Command(
    path=("adapter", OPERATION),
    help=f"answer {OPERATION}, the request read on stdin",
    group_help="answer one operation of the configured client adapter, or print the matrix of every adapter",
    run=adapter_probe,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
    describe_diagnostics=describe_configured_client_answer,
    select_document=attrgetter("document"),
)
