from dataclasses import asdict
from datetime import UTC, date, datetime, time, timedelta

from brigade.command import Argument, Command, ExclusiveArguments
from brigade.errors import UsageError
from brigade.ledger.describe_overview import describe_overview
from brigade.ledger.describe_project import describe_project
from brigade.ledger.describe_skipped_lines import describe_skipped_lines
from brigade.ledger.describe_wave import describe_wave
from brigade.ledger.format_steps_lines import format_steps_lines
from brigade.ledger.read_ledger import read_ledger
from brigade.runtime import Runtime
from brigade.system.read_since import read_since

DOCUMENT_SCHEMA_VERSION = 1
NONE = "none"
MILLISECONDS_PER_MINUTE = 60000
MINUTES_PER_HOUR = 60
STEPS_INDENT = "    "


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
        f"tasks: {_join_or_none(document['tasks'])}",
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


RENDERERS = {"overview": _render_overview, "wave": _render_wave, "project": _render_project}


def _render_text(document: dict) -> str:
    return "\n".join(RENDERERS[document["view"]](document))


def _read_request(options):
    if options.since is not None and options.project is None:
        raise UsageError("--since needs --project")
    return options


def ledger(request, runtime: Runtime) -> dict:
    reading = read_ledger(runtime.paths.state_root)
    if request.wave is not None:
        view = describe_wave(reading, request.wave)
    elif request.project is not None:
        view = describe_project(reading, request.project, _resolve_since(request.since, runtime.now))
    else:
        view = describe_overview(reading)
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, **view, "skipped": [asdict(line) for line in reading.skipped]}


COMMAND = Command(
    path=("ledger",),
    help="read the event journal: an overview, a wave or a project",
    arguments=(
        ExclusiveArguments(
            (
                Argument(("--wave",), {"help": "the tasks, steps, pauses, hand-overs and parked tasks of a wave"}),
                Argument(
                    ("--project",),
                    {"help": "the waves, orders, pull requests, signals, patterns and constraints of a project"},
                ),
            )
        ),
        Argument(("--since",), {"type": read_since, "help": "with --project, <n>d or a day YYYY-MM-DD in UTC"}),
    ),
    run=ledger,
    read_request=_read_request,
    render_text=_render_text,
    describe_diagnostics=describe_skipped_lines,
)
