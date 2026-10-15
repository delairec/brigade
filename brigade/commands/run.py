import argparse
import dataclasses
import time

from brigade.command import Argument, Command
from brigade.runs.create_run_directory import create_run_directory
from brigade.runs.decide_run_exit_code import decide_run_exit_code
from brigade.runs.describe_skipped_runs import describe_skipped_runs
from brigade.runs.detach_run import detach_run
from brigade.runs.plan_run import RunPlan, RunRequest, plan_run
from brigade.runs.prune_runs import PruneRequest, prune_runs
from brigade.runs.read_run_setting import read_run_setting
from brigade.runs.run_locations import PROCESSES_FILE
from brigade.runs.run_segments import run_segments
from brigade.runtime import Runtime
from brigade.system.read_configuration import SLOTS, Configuration, read_configuration
from brigade.system.require_login_environment import LoginDemand, require_login_environment
from brigade.system.stop_signal_receiver import StopSignalReceiver

DOCUMENT_SCHEMA_VERSION = 1
SINGLE_SEGMENT = 1
FORGE_NAME = "github"
UNBOUND_ENVIRONMENT = {}


def _read_forge_environment(configuration: Configuration, slot: str, runtime: Runtime) -> dict:
    login = configuration.forge_accounts.get(slot)
    if login is None:
        return UNBOUND_ENVIRONMENT
    demand = LoginDemand(
        forge=runtime.resolve_plugin("forge", FORGE_NAME),
        forge_name=FORGE_NAME,
        login=login,
        key=slot,
        attempts=configuration.forge_attempts,
    )
    return require_login_environment(demand, runtime, time.sleep)


def _read_run_request(request) -> RunRequest:
    return RunRequest(
        procedure=request.procedure,
        slot=request.slot,
        project=request.project,
        cwd=request.cwd,
        brief=request.brief,
        arguments=tuple(request.arguments),
        run_id=request.run_id,
    )


def _attach_warnings(document: dict, warnings: list[str]) -> dict:
    if not warnings:
        return document
    return {**document, "warnings": warnings}


def _name_segments(count: int) -> str:
    if count == SINGLE_SEGMENT:
        return f"{count} segment"
    return f"{count} segments"


def _render_text(document: dict) -> str:
    if "outcome" not in document:
        return document["run"]
    return (
        f"run {document['run']}: {document['procedure']} as {document['role']} ({document['slot']})"
        f" {document['outcome']} after {_name_segments(document['segments'])}"
    )


def _read_request(options):
    return argparse.Namespace(**{**vars(options), "arguments": options.extra_arguments})


def _accept_extra_argument(extra: str) -> bool:
    return not extra.startswith("-")


def _decide_exit_code(document: dict) -> int:
    return decide_run_exit_code(document.get("outcome", "done"))


def _describe_diagnostics(document: dict) -> list[str]:
    return document.get("warnings", [])


def _prepare_run(request, configuration: Configuration, runtime: Runtime) -> RunPlan:
    run_request = _read_run_request(request)
    forge_environment = _read_forge_environment(configuration, run_request.slot, runtime)
    setting = read_run_setting(run_request.project, configuration, runtime)
    client_adapter = runtime.resolve_plugin("client", setting.client)
    document = runtime.resolve_plugin("document", configuration.document)
    plan = dataclasses.replace(
        plan_run(run_request, setting, client_adapter, document, runtime), forge_environment=forge_environment
    )
    create_run_directory(plan, runtime)
    runtime.trail.locate(plan.run_directory / PROCESSES_FILE)
    return plan


def run(request, runtime: Runtime) -> dict:
    configuration = read_configuration(runtime.paths.configuration_file)
    if request.detach:
        plan = _prepare_run(request, configuration, runtime)
        pid = detach_run(plan, runtime)
        return _attach_warnings(
            {"schema_version": DOCUMENT_SCHEMA_VERSION, "run": plan.run_id, "pid": pid}, list(plan.warnings)
        )
    with StopSignalReceiver() as stop:
        plan = _prepare_run(request, configuration, runtime)
        records = run_segments(plan, runtime, stop)
    pruned = prune_runs(PruneRequest(paths=runtime.paths, keep=configuration.runs_kept))
    document = {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "run": plan.run_id,
        "procedure": plan.procedure.name,
        "slot": plan.slot,
        "role": plan.role.role,
        "client": plan.client,
        "project": plan.project,
        "segments": len(records),
        "outcome": records[-1].result.outcome,
    }
    return _attach_warnings(document, [*plan.warnings, *describe_skipped_runs(pruned.skipped)])


COMMAND = Command(
    path=("run",),
    help="run a procedure as a slot through the client adapter",
    arguments=(
        Argument(
            ("procedure",),
            {
                "help": "a procedure name, or the path of its Markdown file; its arguments, key=value words, follow it"
                " before or after the options"
            },
        ),
        Argument(("--slot",), {"required": True, "choices": SLOTS, "help": "the slot the run takes its role from"}),
        Argument(("--project",), {"help": "the registered project the run belongs to"}),
        Argument(("--cwd",), {"help": "the directory the client runs in; the project's path, else the current one"}),
        Argument(("--brief",), {"help": "a file whose text the run receives as its brief"}),
        Argument(("--detach",), {"action": "store_true", "help": "run in the background and print the run id"}),
        Argument(("--run-id",), {"help": argparse.SUPPRESS}),
    ),
    run=run,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
    describe_diagnostics=_describe_diagnostics,
    accept_extra_argument=_accept_extra_argument,
)
