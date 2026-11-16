from brigade.ledger.format_duration import format_duration
from brigade.ledger.format_run_measures import format_run_measures
from brigade.ledger.format_steps_lines import format_steps_lines

NONE = "none"
STEPS_INDENT = "    "
USAGE_LABELS = {
    "input_tokens": "input",
    "output_tokens": "output",
    "cache_creation_input_tokens": "cache creation",
    "cache_read_input_tokens": "cache read",
}


def _join_or_none(items: list[str]) -> str:
    return ", ".join(items) if items else NONE


def _render_cost_line(cost_usd: float | None) -> str:
    return f"cost: {NONE if cost_usd is None else f'{cost_usd:.2f} USD'}"


def _render_tokens_line(usage: dict | None) -> str:
    if usage is None:
        return f"tokens: {NONE}"
    return f"tokens: {', '.join(f'{label} {usage[name]}' for name, label in USAGE_LABELS.items())}"


def _render_task_rows(rows: list[dict]) -> list[str]:
    if not rows:
        return [f"tasks: {NONE}"]
    return ["tasks:", *(f"  {row['task']}  {format_run_measures(row)}" for row in rows)]


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
    return f"  {pause['paused_at']} to {pause['resumed_at']}  {format_duration(pause['duration_ms'])}"


def _render_event(entry: dict) -> str:
    task = entry["fields"].get("task")
    subject = "" if task is None else f"  {task}"
    return f"  {entry['at']}  {entry['event']}{subject}"


def render_wave_lines(document: dict) -> list[str]:
    pull_requests = [f"#{item['pr']} {item['task']} rounds {item['rounds']}" for item in document["pull_requests"]]
    handovers = [
        f"{item['task']} {item['role']} {item['slot']} segment {item['segment']}" for item in document["handovers"]
    ]
    return [
        (
            f"wave {document['wave']}: {document['first']} to {document['last']},"
            f" wall time {format_duration(document['wall_time_ms'])}"
        ),
        _render_cost_line(document["cost_usd"]),
        _render_tokens_line(document["usage"]),
        *_render_task_rows(document["by_task"]),
        f"pull requests: {_join_or_none(pull_requests)}",
        *_render_steps("steps by slot", document["steps"]["by_slot"]),
        *_render_steps("steps by role", document["steps"]["by_role"]),
        f"pauses: {len(document['pauses'])}, {format_duration(document['paused_ms'])} in all",
        *(_render_pause(pause) for pause in document["pauses"]),
        f"handovers: {_join_or_none(handovers)}",
        f"parked: {_join_or_none(document['parked'])}",
        "events:",
        *(_render_event(entry) for entry in document["events"]),
    ]
