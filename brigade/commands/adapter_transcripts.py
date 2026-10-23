import argparse
import sys
from operator import attrgetter

from brigade.command import Command
from brigade.runtime import Runtime
from brigade.system.ask_configured_client import ConfiguredClientAnswer, ask_configured_client
from brigade.system.describe_configured_client_answer import describe_configured_client_answer
from brigade.system.read_client_request import read_client_request
from brigade.system.read_configured_client import read_configured_client
from brigade.system.render_json import render_json

OPERATION = "transcripts"


def _read_request(options) -> str:
    return sys.stdin.read()


def adapter_transcripts(request: argparse.Namespace, runtime: Runtime) -> ConfiguredClientAnswer:
    client_request = read_client_request(OPERATION, request)
    configured = read_configured_client(runtime)
    client = runtime.resolve_plugin("client", configured.name)
    return ask_configured_client(client, configured, client_request, runtime)


COMMAND = Command(
    path=("adapter", OPERATION),
    help=f"answer {OPERATION}, the request read on stdin",
    group_help="answer one operation of the configured client adapter, or print the matrix of every adapter",
    run=adapter_transcripts,
    read_request=_read_request,
    render_text=render_json,
    describe_diagnostics=describe_configured_client_answer,
    select_document=attrgetter("document"),
)
