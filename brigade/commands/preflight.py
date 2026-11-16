import argparse
from pathlib import Path

from brigade.command import Argument, Command
from brigade.commands._accept_parameter import accept_parameter
from brigade.commands._equip_collector import equip_collector
from brigade.commands._read_parameters import read_parameters
from brigade.git.locate_main_checkout import locate_main_checkout
from brigade.git.locate_worktree_root import locate_worktree_root
from brigade.preflights.run_preflight import BUILT_IN_PREFLIGHTS, PreflightRun, run_preflight
from brigade.runtime import Runtime
from brigade.system.check_shapes import FAILED

DOCUMENT_SCHEMA_VERSION = 1


def _render_text(document: dict) -> str:
    lines = [f"preflight {document['preflight']}"]
    for check in document["checks"]:
        lines.append(f"{check['verdict']}  {check['name']}")
        lines.extend(f"  {finding}" for finding in check["findings"])
    return "\n".join(lines)


def _decide_exit_code(document: dict) -> int:
    return int(document["verdict"] == FAILED)


def preflight(request: argparse.Namespace, runtime: Runtime) -> dict:
    project = locate_main_checkout(runtime.run_process, locate_worktree_root(runtime.run_process, Path.cwd()))
    parameters = read_parameters(request.extra_arguments)
    run = PreflightRun(
        name=request.name,
        project=project,
        parameters=parameters,
        equipment=equip_collector(project, runtime),
        preflights=BUILT_IN_PREFLIGHTS,
    )
    outcome = run_preflight(run, runtime)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "preflight": request.name,
        "parameters": parameters,
        "verdict": outcome.verdict,
        "checks": outcome.checks,
    }


COMMAND = Command(
    path=("preflight",),
    help="run the collectors and the checks of a named preflight; key=value pairs are their parameters",
    arguments=(Argument(("name",), {"help": "the name of the preflight"}),),
    run=preflight,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
    accept_extra_argument=accept_parameter,
)
