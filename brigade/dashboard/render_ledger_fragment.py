from html import escape
from urllib.parse import quote

from brigade.dashboard.render_answer import render_answer
from brigade.dashboard.render_html_table import render_html_table
from brigade.dashboard.run_routed_command import CommandAnswer

ABSENT = "-"
MILLISECONDS_PER_MINUTE = 60000
FIRST_DAY = "01"
STEPS_HEADER = ("runs", "p50", "p90")
COMPARED_MEASURES = {
    "steps": "steps",
    "steps_to_first_edit": "steps to first edit",
    "oversized_output_steps": "oversized output steps",
}
PERIODS = ("before", "from")


def _show(value: object) -> str:
    return ABSENT if value is None else escape(str(value))


def _link(query: str, value: str, label: str) -> str:
    address = f"#ledger?{query}={quote(value, safe='')}"
    return f'<a href="{escape(address)}">{escape(label)}</a>'


def _render_steps(name: str, runs: dict) -> tuple[str, ...]:
    return (escape(name), str(runs["measured"]), _show(runs["p50"]), _show(runs["p90"]))


def _render_budgets(document: dict) -> str:
    rows = [
        (*_render_steps(name, summary["runs"]), "yes" if summary["estimate"] else "no")
        for name, summary in document["procedures"].items()
    ]
    return render_html_table(("procedure", *STEPS_HEADER, "estimate"), rows, "no run finished")


def _render_month(month: str, waves: list[str]) -> tuple[str, ...]:
    day = f"{month}-{FIRST_DAY}"
    return (
        escape(month),
        str(len(waves)),
        " ".join(_link("wave", wave, wave) for wave in waves),
        _link("before", day, f"compare before {day}"),
    )


def _render_months(document: dict) -> str:
    rows = [_render_month(month, waves) for month, waves in document["waves_started"].items()]
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


def _render_comparison(document: dict) -> str:
    day = escape(document["before"])
    periods = document["periods"]
    rows = [
        (label, *(cell for period in PERIODS for cell in _render_percentiles(periods[period][measure])))
        for measure, label in COMPARED_MEASURES.items()
    ]
    header = ("measure", "p50 before", "p90 before", "p50 from", "p90 from")
    return (
        f"<p>{periods['before']['runs']} runs before {day}, {periods['from']['runs']} runs from it on</p>"
        f"{render_html_table(header, rows, 'no measure')}"
    )


SECTIONS = (
    ("budgets", "Steps by procedure", _render_budgets),
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
