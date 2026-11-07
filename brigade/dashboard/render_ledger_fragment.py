from datetime import date, timedelta
from html import escape
from urllib.parse import quote

from brigade.dashboard.render_answer import render_answer
from brigade.dashboard.render_html_table import render_html_table
from brigade.dashboard.run_routed_command import CommandAnswer

ABSENT = "-"
MILLISECONDS_PER_MINUTE = 60000
FIRST_DAY = "01"
STEPS_HEADER = ("runs", "p50", "p90")
ROLE_BUDGET_HEADER = ("role", "shipped", "computed", "applied", "segments", "restarts", "g", "R")
COMPARED_MEASURES = {
    "steps": "steps",
    "steps_to_first_edit": "steps to first edit",
    "oversized_output_steps": "oversized output steps",
}
DAY_LENGTH = len("YYYY-MM-DD")
PREVIOUS_DAY = timedelta(days=1)


def _show(value: object) -> str:
    return ABSENT if value is None else escape(str(value))


def _link(query: str, value: str, label: str) -> str:
    address = f"#ledger?{query}={quote(value, safe='')}"
    return f'<a href="{escape(address)}">{escape(label)}</a>'


def _render_steps(name: str, runs: dict) -> tuple[str, ...]:
    return (escape(name), str(runs["measured"]), _show(runs["p50"]), _show(runs["p90"]))


def _show_tokens(tokens: float | None) -> str:
    return ABSENT if tokens is None else str(round(tokens))


def _render_role_budget(role: str, budget: dict) -> tuple[str, ...]:
    counts = (budget[name] for name in ("shipped", "computed", "applied", "segments", "restarts"))
    return (
        escape(role),
        *(_show(count) for count in counts),
        _show_tokens(budget["growth"]),
        _show_tokens(budget["restart_tokens"]),
    )


def _render_budgets(document: dict) -> str:
    rows = [
        (*_render_steps(name, summary["runs"]), "yes" if summary["estimate"] else "no")
        for name, summary in document["procedures"].items()
    ]
    roles = [_render_role_budget(role, budget) for role, budget in document["roles"].items()]
    return (
        render_html_table(("procedure", *STEPS_HEADER, "estimate"), rows, "no run finished")
        + "<h3>Step cap by role</h3>"
        + render_html_table(ROLE_BUDGET_HEADER, roles, "no role measured")
    )


def _link_comparison(day: str, first_day: str, last_day: str) -> str:
    day_before = (date.fromisoformat(day) - PREVIOUS_DAY).isoformat()
    ranges = (f"{first_day}..{day_before}", f"{day}..{last_day}")
    address = "#ledger?" + "&".join(f"range={quote(day_range, safe='')}" for day_range in ranges)
    return f'<a href="{escape(address)}">{escape(f"compare before {day}")}</a>'


def _render_month(month: str, waves: list[str], overview: dict) -> tuple[str, ...]:
    day = f"{month}-{FIRST_DAY}"
    return (
        escape(month),
        str(len(waves)),
        " ".join(_link("wave", wave, wave) for wave in waves),
        _link_comparison(day, overview["first"][:DAY_LENGTH], overview["last"][:DAY_LENGTH]),
    )


def _render_months(document: dict) -> str:
    rows = [_render_month(month, waves, document) for month, waves in document["waves_started"].items()]
    return render_html_table(("month", "waves", "started", "baseline"), rows, "no wave started")


def _render_pause(pause: dict) -> tuple[str, ...]:
    if pause["resumed_at"] is None:
        return (escape(pause["paused_at"]), "still paused", ABSENT)
    minutes = pause["duration_ms"] // MILLISECONDS_PER_MINUTE
    return (escape(pause["paused_at"]), escape(pause["resumed_at"]), str(minutes))


def _render_wave(document: dict) -> str:
    roles = [_render_steps(role, summary["runs"]) for role, summary in document["steps"]["by_role"].items()]
    pauses = [_render_pause(pause) for pause in document["pauses"]]
    return (
        f"<p>wave {escape(document['wave'])}</p>"
        f"{render_html_table(('role', *STEPS_HEADER), roles, 'no run finished')}"
        f"{render_html_table(('paused at', 'resumed at', 'minutes'), pauses, 'no pause')}"
    )


def _render_percentiles(summary: dict | None) -> tuple[str, str]:
    if summary is None:
        return (ABSENT, ABSENT)
    return (_show(summary["runs"]["p50"]), _show(summary["runs"]["p90"]))


def _name_range(day_range: dict) -> str:
    return f"{day_range['start']} to {day_range['end']}"


def _render_comparison(document: dict) -> str:
    ranges = document["ranges"]
    rows = [
        (label, *(cell for day_range in ranges for cell in _render_percentiles(day_range[measure])))
        for measure, label in COMPARED_MEASURES.items()
    ]
    header = (
        "measure",
        *(escape(f"{percentile} {_name_range(day_range)}") for day_range in ranges for percentile in ("p50", "p90")),
    )
    counts = ", ".join(escape(f"{day_range['runs']} runs from {_name_range(day_range)}") for day_range in ranges)
    return f"<p>{counts}</p>{render_html_table(header, rows, 'no measure')}"


SECTIONS = (
    ("budgets", "Steps by procedure and step cap by role", _render_budgets),
    ("overview", "Waves started by month", _render_months),
    ("wave", "Steps by role and pauses of the wave", _render_wave),
    ("comparison", "Baseline comparison", _render_comparison),
)


def render_ledger_fragment(answers: dict[str, CommandAnswer]) -> str:
    return "".join(
        f"<section><h2>{heading}</h2>{render_answer(answers[name], render)}</section>"
        for name, heading, render in SECTIONS
        if name in answers
    )
