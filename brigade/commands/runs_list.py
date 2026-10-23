import argparse

from brigade.command import Argument, Command
from brigade.runs.list_runs import list_runs
from brigade.runtime import Runtime
from brigade.system.render_table import render_table

DOCUMENT_SCHEMA_VERSION = 1
ABSENT = "-"
NO_RUNS = "no runs"
COLUMNS = ("run", "procedure", "slot", "role", "project", "state", "outcome")


def _render_value(value) -> str:
    if value is None:
        return ABSENT
    return value


def _render_text(document: dict) -> str:
    if not document["runs"]:
        return NO_RUNS
    return render_table(
        COLUMNS, [tuple(_render_value(listed[column]) for column in COLUMNS) for listed in document["runs"]]
    )


def _describe_skipped_runs(document: dict) -> list[str]:
    return [f"skipped run {skipped['run']}: {skipped['reason']}" for skipped in document["skipped"]]


def _is_selected(listed: dict, request) -> bool:
    return (request.wave is None or listed["wave"] == request.wave) and (
        request.task is None or listed["task"] == request.task
    )


def runs_list(request: argparse.Namespace, runtime: Runtime) -> dict:
    listing = list_runs(runtime.paths.state_root)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "runs": [listed for listed in listing["runs"] if _is_selected(listed, request)],
        "skipped": listing["skipped"],
    }


COMMAND = Command(
    path=("runs", "list"),
    help="list every run with its state and outcome",
    group_help="list the runs, show one, stop one and prune them",
    arguments=(
        Argument(("--wave",), {"help": "keep the runs of this wave"}),
        Argument(("--task",), {"help": "keep the runs of this task"}),
    ),
    run=runs_list,
    render_text=_render_text,
    describe_diagnostics=_describe_skipped_runs,
)
