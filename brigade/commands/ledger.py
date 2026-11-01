import argparse
from dataclasses import asdict, replace
from datetime import UTC, date, datetime, time, timedelta

from brigade.command import Argument, Command, ExclusiveArguments
from brigade.ledger.describe_overview import describe_overview
from brigade.ledger.describe_project import describe_project
from brigade.ledger.describe_skipped_lines import describe_skipped_lines
from brigade.ledger.describe_task import describe_task
from brigade.ledger.describe_wave import describe_wave
from brigade.ledger.format_instant import format_instant
from brigade.ledger.format_steps_lines import format_steps_lines
from brigade.ledger.read_ledger import LedgerReading, read_ledger
from brigade.runtime import Runtime
from brigade.system.read_since import read_since

DOCUMENT_SCHEMA_VERSION = 1
NONE = "none"
MILLISECONDS_PER_MINUTE = 60000
MINUTES_PER_HOUR = 60
STEPS_INDENT = "    "
ABSENT = "-"
USAGE_LABELS = {
    "input_tokens": "input",
    "output_tokens": "output",
    "cache_creation_input_tokens": "cache creation",
    "cache_read_input_tokens": "cache read",
}


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


def _join_or_none(items: list[str]) -> str:
    return ", ".join(items) if items else NONE


def _format_duration(milliseconds: int) -> str:
    hours, minutes = divmod(milliseconds // MILLISECONDS_PER_MINUTE, MINUTES_PER_HOUR)
    return f"{hours}h{minutes:02d}m"


def _show_steps(steps: int | None) -> str:
    return ABSENT if steps is None else str(steps)


def _show_run_steps(run: dict) -> str:
    steps = _show_steps(run["steps"])
    return f"{steps} partial" if run["partial"] else steps


def _show_duration(milliseconds: int | None) -> str:
    return ABSENT if milliseconds is None else _format_duration(milliseconds)


def _show_cost(cost_usd: float | None) -> str:
    return ABSENT if cost_usd is None else f"{cost_usd:.2f} USD"


def _render_cost_line(cost_usd: float | None) -> str:
    return f"cost: {NONE if cost_usd is None else _show_cost(cost_usd)}"


def _render_tokens_line(usage: dict | None) -> str:
    if usage is None:
        return f"tokens: {NONE}"
    return f"tokens: {', '.join(f'{label} {usage[name]}' for name, label in USAGE_LABELS.items())}"


def _render_task_rows(rows: list[dict]) -> list[str]:
    if not rows:
        return [f"tasks: {NONE}"]
    return [
        "tasks:",
        *(
            f"  {row['task']}  steps {_show_run_steps(row)}"
            f"  duration {_show_duration(row['duration_ms'])}  cost {_show_cost(row['cost_usd'])}"
            for row in rows
        ),
    ]


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


def _render_steps(heading: str, summaries: dict) -> list[str]:
    if not summaries:
        return [f"{heading}: {NONE}"]
    lines = [f"{heading}:"]
    for name, steps in summaries.items():
        lines.extend([f"  {name}", *format_steps_lines(STEPS_INDENT, steps)])
    return lines


def _render_pause(pause: dict) -> str:
    if pause["resumed_at"] is None:
        return f"  {pause['paused_at']}, still paused"
    return f"  {pause['paused_at']} to {pause['resumed_at']}  {_format_duration(pause['duration_ms'])}"


def _render_wave(document: dict) -> list[str]:
    pull_requests = [f"#{item['pr']} {item['task']} rounds {item['rounds']}" for item in document["pull_requests"]]
    hand_overs = [
        f"{item['task']} {item['role']} {item['slot']} segment {item['segment']}" for item in document["hand_overs"]
    ]
    return [
        (
            f"wave {document['wave']}: {document['first']} to {document['last']},"
            f" wall time {_format_duration(document['wall_time_ms'])}"
        ),
        _render_cost_line(document["cost_usd"]),
        _render_tokens_line(document["usage"]),
        *_render_task_rows(document["by_task"]),
        f"pull requests: {_join_or_none(pull_requests)}",
        *_render_steps("steps by slot", document["steps"]["by_slot"]),
        *_render_steps("steps by role", document["steps"]["by_role"]),
        f"pauses: {len(document['pauses'])}, {_format_duration(document['paused_ms'])} in all",
        *(_render_pause(pause) for pause in document["pauses"]),
        f"hand-overs: {_join_or_none(hand_overs)}",
        f"parked: {_join_or_none(document['parked'])}",
    ]


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
    return (
        f"  {run['run']}  {run['finished_at']}  {run['slot']}  {run['outcome']}"
        f"  steps {_show_run_steps(run)}  duration {_show_duration(run['duration_ms'])}"
        f"  cost {_show_cost(run['cost_usd'])}"
    )


def _render_task(document: dict) -> list[str]:
    return [f"task {document['task']}: {len(document['runs'])} runs", *(_render_run(run) for run in document["runs"])]


RENDERERS = {"overview": _render_overview, "wave": _render_wave, "task": _render_task, "project": _render_project}


def _render_text(document: dict) -> str:
    return "\n".join(RENDERERS[document["view"]](document))


def _select_since(reading: LedgerReading, since: datetime | None) -> LedgerReading:
    return replace(
        reading, entries=tuple(entry for entry in reading.entries if since is None or entry.instant >= since)
    )


def _describe_view(reading: LedgerReading, request: argparse.Namespace) -> dict:
    if request.wave is not None:
        return describe_wave(reading, request.wave)
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
    help="read the event journal: an overview, a wave, a task or a project",
    arguments=(
        ExclusiveArguments(
            (
                Argument(
                    ("--wave",),
                    {"help": "the cost, tokens, tasks, steps, pauses, hand-overs and parked tasks of a wave"},
                ),
                Argument(("--task",), {"help": "the runs of a task, their outcome, steps, duration and cost"}),
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
