import argparse

from brigade.command import Argument, Command
from brigade.ledger.format_duration import format_duration
from brigade.runs.format_run_arguments import format_run_arguments
from brigade.runs.list_runs import list_runs
from brigade.runs.list_segment_outcomes import list_segment_outcomes
from brigade.runs.summarize_run import summarize_run
from brigade.runtime import Runtime
from brigade.system.render_table import render_table

DOCUMENT_SCHEMA_VERSION = 1
ABSENT = "-"
NO_RUNS = "no runs"
COLUMNS = ("run", "procedure", "slot", "role", "project", "wave", "task", "state", "outcome")
SEGMENT_SEPARATOR = ","
PARTIAL_MARK = " partial"
MEASURED_COLUMNS = ("segments", "duration", "cost", "arguments")
RUN_STATES = ("running", "finished", "dead")


def _render_value(value) -> str:
    if value is None:
        return ABSENT
    return value


def _render_measure(value: str | None, *, partial: bool) -> str:
    if value is None:
        return ABSENT
    return f"{value}{PARTIAL_MARK}" if partial else value


def _render_duration(listed: dict) -> str:
    duration_ms = listed["duration_ms"]
    shown = None if duration_ms is None else format_duration(duration_ms)
    return _render_measure(shown, partial=listed["duration_partial"])


def _render_cost(listed: dict) -> str:
    cost_usd = listed["cost_usd"]
    shown = None if cost_usd is None else f"{cost_usd:.2f} USD"
    return _render_measure(shown, partial=listed["cost_partial"])


def _render_row(listed: dict) -> tuple[str, ...]:
    return (
        *(_render_value(listed[column]) for column in COLUMNS),
        SEGMENT_SEPARATOR.join(list_segment_outcomes(listed["state"], listed["segments"])) or ABSENT,
        _render_duration(listed),
        _render_cost(listed),
        format_run_arguments(listed["arguments"]),
    )


def _render_text(document: dict) -> str:
    if not document["runs"]:
        return NO_RUNS
    return render_table((*COLUMNS, *MEASURED_COLUMNS), [_render_row(listed) for listed in document["runs"]])


def _describe_skipped_runs(document: dict) -> list[str]:
    return [f"skipped run {skipped['run']}: {skipped['reason']}" for skipped in document["skipped"]]


def _is_selected(listed: dict, request) -> bool:
    return (
        (request.wave is None or listed["wave"] == request.wave)
        and (request.task is None or listed["task"] == request.task)
        and (request.state is None or listed["state"] == request.state)
    )


def run_list(request: argparse.Namespace, runtime: Runtime) -> dict:
    listing = list_runs(runtime.paths.state_root, summarize_run)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "runs": [listed for listed in listing["runs"] if _is_selected(listed, request)],
        "skipped": listing["skipped"],
    }


COMMAND = Command(
    path=("run", "list"),
    help="list every run with its state and outcome",
    group_help="start a procedure as a slot through the client adapter, list the runs, show one, stop one and prune them",
    arguments=(
        Argument(("--wave",), {"help": "keep the runs of this wave"}),
        Argument(("--task",), {"help": "keep the runs of this task"}),
        Argument(("--state",), {"choices": RUN_STATES, "help": "keep the runs in this state"}),
    ),
    run=run_list,
    render_text=_render_text,
    describe_diagnostics=_describe_skipped_runs,
)
