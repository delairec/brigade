import argparse
import sys
from operator import attrgetter

from brigade.command import Command
from brigade.runtime import Runtime
from brigade.system.ask_configured_client import ConfiguredClientAnswer, ask_configured_client
from brigade.system.describe_configured_client_answer import describe_configured_client_answer
from brigade.system.read_client_request import read_client_request
from brigade.system.read_configuration import CONFIGURATION_REQUIRED, read_configuration
from brigade.system.render_json import render_json
from brigade.system.require_configured_client import require_configured_client

OPERATION = "resume-argv"


def _read_request(options) -> str:
    return sys.stdin.read()


def adapter_resume_argv(request: argparse.Namespace, runtime: Runtime) -> ConfiguredClientAnswer:
    client_request = read_client_request(OPERATION, request)
    configured = require_configured_client(
        read_configuration(runtime, CONFIGURATION_REQUIRED), runtime.paths.configuration_file
    )
    client = runtime.resolve_plugin("client", configured.name)
    return ask_configured_client(client, configured, client_request, runtime)


COMMAND = Command(
    path=("adapter", OPERATION),
    help=f"answer {OPERATION}, the request read on stdin",
    group_help="answer one operation of the configured client adapter, or print the matrix of every adapter",
    run=adapter_resume_argv,
    read_request=_read_request,
    render_text=render_json,
    describe_diagnostics=describe_configured_client_answer,
    select_document=attrgetter("document"),
)
