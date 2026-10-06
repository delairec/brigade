from brigade.commands.format_steps_line import format_steps_line

NONE = "none"
MILLISECONDS_PER_MINUTE = 60000
MINUTES_PER_HOUR = 60


def _join_counts(counts: dict) -> str:
    return ", ".join(f"{name} {count}" for name, count in counts.items())


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
    if runs["outcomes"]:
        lines.append(f"runs finished: {_join_counts(runs['outcomes'])}")
    if runs["error_classes"]:
        lines.append(f"error classes: {_join_counts(runs['error_classes'])}")
    return lines


def _render_steps(heading: str, summaries: dict) -> list[str]:
    if not summaries:
        return [f"{heading}: {NONE}"]
    width = max(len(name) for name in summaries)
    return [f"{heading}:", *(format_steps_line(name, width, summary) for name, summary in summaries.items())]


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
        f"wave {document['wave']}: {document['first']} to {document['last']},"
        f" wall time {_format_duration(document['wall_time_ms'])}",
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


def render_ledger_text(document: dict) -> str:
    return "\n".join(RENDERERS[document["view"]](document))
