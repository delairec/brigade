import argparse

from brigade.command import Argument, Command
from brigade.runs.create_run_directory import create_run_directory
from brigade.runs.detach_run import detach_run
from brigade.runs.plan_run import RunPlan, RunRequest, plan_run
from brigade.runs.run_segments import run_segments
from brigade.system.read_configuration import SLOTS

DOCUMENT_SCHEMA_VERSION = 1
ARGUMENT_SEPARATOR = "="
SINGLE_SEGMENT = 1


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


def _attach_warnings(document: dict, plan: RunPlan) -> dict:
    if not plan.warnings:
        return document
    return {**document, "warnings": list(plan.warnings)}


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
    return argparse.Namespace(**{**vars(options), "arguments": [*options.arguments, *options.extra_arguments]})


def _accept_extra_argument(extra: str) -> bool:
    return not extra.startswith("-") and ARGUMENT_SEPARATOR in extra


def _decide_exit_code(document: dict) -> int:
    if document.get("outcome", "done") != "done":
        return 1
    return 0


def _describe_diagnostics(document: dict) -> list[str]:
    return document.get("warnings", [])


def run(request, runtime) -> dict:
    plan = plan_run(_read_run_request(request), runtime)
    create_run_directory(plan)
    if request.detach:
        pid = detach_run(plan, runtime)
        return _attach_warnings({"schema_version": DOCUMENT_SCHEMA_VERSION, "run": plan.run_id, "pid": pid}, plan)
    records = run_segments(plan, runtime)
    document = {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "run": plan.run_id,
        "procedure": plan.procedure.name,
        "slot": plan.slot,
        "role": plan.role.role,
        "client": plan.client,
        "project": plan.project,
        "segments": len(records),
        "outcome": records[-1].result["outcome"],
    }
    return _attach_warnings(document, plan)


COMMAND = Command(
    path=("run",),
    help="run a procedure as a slot through the client adapter",
    arguments=(
        Argument(("procedure",), {"help": "a procedure name, or the path of its Markdown file"}),
        Argument(("--slot",), {"required": True, "choices": SLOTS, "help": "the slot the run takes its role from"}),
        Argument(("--project",), {"help": "the registered project the run belongs to"}),
        Argument(("--cwd",), {"help": "the directory the client runs in; the project's path, else the current one"}),
        Argument(("--brief",), {"help": "a file whose text the run receives as its brief"}),
        Argument(("--detach",), {"action": "store_true", "help": "run in the background and print the run id"}),
        Argument(("--run-id",), {"help": argparse.SUPPRESS}),
        Argument(("arguments",), {"nargs": "*", "metavar": "key=value", "help": "an argument of the procedure"}),
    ),
    run=run,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
    describe_diagnostics=_describe_diagnostics,
    accept_extra_argument=_accept_extra_argument,
)
