import argparse
from dataclasses import asdict, replace
from datetime import UTC, date, datetime, time, timedelta

from brigade.command import Argument, Command, ExclusiveArguments
from brigade.ledger.describe_overview import describe_overview
from brigade.ledger.describe_project import describe_project
from brigade.ledger.describe_skipped_lines import describe_skipped_lines
from brigade.ledger.describe_task import describe_task
from brigade.ledger.format_instant import format_instant
from brigade.ledger.format_run_measures import format_run_measures
from brigade.ledger.read_ledger import LedgerReading, read_ledger
from brigade.runtime import Runtime
from brigade.system.read_since import read_since

DOCUMENT_SCHEMA_VERSION = 1
NONE = "none"


def _resolve_since(since: timedelta | date | None, now: datetime) -> datetime | None:
    if since is None:
        return None
    if isinstance(since, timedelta):
        return now - since
    return datetime.combine(since, time(), tzinfo=UTC)


def _join_counts(counts: dict) -> str:
    return ", ".join(f"{name} {count}" for name, count in counts.items())


def _join_finished(counts: dict) -> str:
    return ", ".join([str(sum(counts.values())), *(f"{name} {count}" for name, count in counts.items())])


def _join_counts_or_none(counts: dict) -> str:
    return _join_counts(counts) or NONE


def _render_overview(document: dict) -> list[str]:
    events = document["events"]
    period = "" if document["first"] is None else f", from {document['first']} to {document['last']}"
    width = max((len(name) for name in events), default=0)
    lines = [
        f"events: {sum(events.values())}{period}",
        f"files read: {len(document['files'])}",
        f"lines skipped: {len(document['skipped'])}",
        *(f"  {name:<{width}}  {count}" for name, count in events.items()),
    ]
    runs = document["runs"]
    segments = document["segments"]
    if runs["outcomes"]:
        lines.append(f"runs finished: {_join_finished(runs['outcomes'])}")
        lines.append(f"segments finished: {_join_finished(segments['outcomes'])}")
    if segments["error_classes"]:
        lines.append(f"error classes of runs: {_join_counts_or_none(runs['error_classes'])}")
        lines.append(f"error classes of segments: {_join_counts(segments['error_classes'])}")
    return lines


def _render_project(document: dict) -> list[str]:
    since = "" if document["since"] is None else f" since {document['since']}"
    orders = _join_counts(document["orders_done"]) or "0"
    return [
        f"project {document['project']}{since}",
        f"waves started: {document['waves_started']}",
        f"orders done: {orders}",
        f"pull requests merged: {document['pull_requests_merged']}",
        f"signals recorded: {document['signals_recorded']}",
        f"patterns ratified: {document['patterns_ratified']}",
        f"constraints delivered: {document['constraints_delivered']}",
    ]


def _render_run(run: dict) -> str:
    return f"  {run['run']}  {run['finished_at']}  {run['slot']}  {run['outcome']}  {format_run_measures(run)}"


def _render_task(document: dict) -> list[str]:
    return [f"task {document['task']}: {len(document['runs'])} runs", *(_render_run(run) for run in document["runs"])]


RENDERERS = {"overview": _render_overview, "task": _render_task, "project": _render_project}


def _render_text(document: dict) -> str:
    return "\n".join(RENDERERS[document["view"]](document))


def _select_since(reading: LedgerReading, since: datetime | None) -> LedgerReading:
    return replace(
        reading, entries=tuple(entry for entry in reading.entries if since is None or entry.instant >= since)
    )


def _describe_view(reading: LedgerReading, request: argparse.Namespace) -> dict:
    if request.task is not None:
        return describe_task(reading, request.task)
    if request.project is not None:
        return describe_project(reading, request.project)
    return describe_overview(reading)


def ledger(request: argparse.Namespace, runtime: Runtime) -> dict:
    since = _resolve_since(request.since, runtime.now)
    reading = _select_since(read_ledger(runtime.paths.state_root), since)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        **_describe_view(reading, request),
        "since": None if since is None else format_instant(since),
        "skipped": [asdict(line) for line in reading.skipped],
    }


COMMAND = Command(
    path=("ledger",),
    help="read the event journal: an overview, a task or a project",
    arguments=(
        ExclusiveArguments(
            (
                Argument(("--task",), {"help": "the runs of a task, their outcome, turns, duration and cost"}),
                Argument(
                    ("--project",),
                    {"help": "the waves, orders, pull requests, signals, patterns and constraints of a project"},
                ),
            )
        ),
        Argument(
            ("--since",), {"type": read_since, "help": "the events from <n>d ago or from a day YYYY-MM-DD in UTC"}
        ),
    ),
    run=ledger,
    render_text=_render_text,
    describe_diagnostics=describe_skipped_lines,
)
