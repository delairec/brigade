from datetime import date, timedelta
from html import escape
from urllib.parse import quote

from brigade.dashboard.render_answer import render_answer
from brigade.dashboard.render_callout import render_callout
from brigade.dashboard.render_cap_bar import CapBar, render_cap_bar
from brigade.dashboard.render_cap_history import render_cap_history
from brigade.dashboard.render_html_table import render_html_table
from brigade.dashboard.render_stat_tile import StatTile, render_stat_tile
from brigade.dashboard.render_svg_bar import SvgBar, render_svg_bar
from brigade.dashboard.run_routed_command import CommandAnswer

ABSENT = "-"
MILLISECONDS_PER_MINUTE = 60000
FIRST_DAY = "01"
STEPS_HEADER = ("runs", "p50", "p90")
MEASURE_HEADER = "measure"
MEASURE_MARKS = {True: "estimate", False: "measured"}
MEASURED_SEGMENTS_FOR_A_MEASUREMENT = 5
MEASURED_RUNS_FOR_A_COMPARISON = 5
TICKS_OF_A_DAY = 288
PERIMETER_STATE = ""
OVER_CAP_STATE = "turn_limit"
WITHIN_CAP_STATE = "done"
FAILED_ACTION_STATE = "failed"
UNMEASURED_OVERSHOOT = -1
CAPS_HEADER = ("role", "segment p90", "share of the applied cap", "against the cap", MEASURE_HEADER)
ROLE_BUDGET_HEADER = ("role", "shipped", "computed", "applied", "segments", "restarts", "g", "R")
COMPARED_MEASURES = {
    "turns": "turns",
    "turns_to_first_edit": "turns to first edit",
    "oversized_output_turns": "oversized output turns",
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


def _measure_overshoot(budget: dict) -> float:
    if budget["segment_p90"] is None:
        return UNMEASURED_OVERSHOOT
    return budget["segment_p90"] / budget["applied"]


def _render_cap_fit(role: str, budget: dict) -> tuple[str, ...]:
    estimate = MEASURE_MARKS[budget["segments"] < MEASURED_SEGMENTS_FOR_A_MEASUREMENT]
    p90 = budget["segment_p90"]
    if p90 is None:
        return (escape(role), ABSENT, ABSENT, ABSENT, estimate)
    applied = budget["applied"]
    bar = CapBar(
        label=f"segment p90 {p90} of {role} against its cap of {applied}",
        state=OVER_CAP_STATE if p90 > applied else WITHIN_CAP_STATE,
        value=p90,
        cap=applied,
    )
    share = f"{round(100 * p90 / applied)}% of {applied}"
    return (escape(role), str(p90), escape(share), render_cap_bar(bar), estimate)


def _render_caps(document: dict) -> str:
    by_overshoot = sorted(document["roles"].items(), key=lambda item: _measure_overshoot(item[1]), reverse=True)
    fits = [_render_cap_fit(role, budget) for role, budget in by_overshoot]
    roles = [_render_role_budget(role, budget) for role, budget in document["roles"].items()]
    histories = "".join(render_cap_history(role, budget) for role, budget in document["roles"].items())
    return (
        render_html_table(CAPS_HEADER, fits, "no role measured")
        + "<h3>Turn cap by role</h3>"
        + render_html_table(ROLE_BUDGET_HEADER, roles, "no role measured")
        + histories
    )


def _render_procedures(document: dict) -> str:
    rows = [
        (*_render_steps(name, summary["runs"]), MEASURE_MARKS[summary["estimate"]])
        for name, summary in document["procedures"].items()
    ]
    return f"<p>Turns over the last {document['last']} runs finished of each procedure.</p>" + render_html_table(
        ("procedure", *STEPS_HEADER, MEASURE_HEADER), rows, "no run finished"
    )


def _name_period(overview: dict) -> str:
    if overview["first"] is None:
        return "in an empty ledger"
    return f"from {overview['first']} to {overview['last']}"


def _count_runs(overview: dict) -> int:
    return sum(overview["runs"]["outcomes"].values())


def _render_coverage(overview: dict) -> str:
    return render_callout(
        PERIMETER_STATE,
        f"The measures cover {_count_runs(overview)} runs finished {_name_period(overview)};"
        f" {len(overview['skipped'])} lines of the ledger skipped, counted in no figure.",
    )


def _render_failed_day(day: str, count: int) -> tuple[str, ...]:
    bar = SvgBar(
        label=f"{count} failed actions for the {TICKS_OF_A_DAY} ticks of {day}",
        state=FAILED_ACTION_STATE,
        value=count,
        total=TICKS_OF_A_DAY,
    )
    return (escape(day), str(count), render_svg_bar(bar))


def _render_failures(overview: dict) -> str:
    failed = overview["failed_actions"]
    days = [_render_failed_day(day, count) for day, count in failed["by_day"].items()]
    by_count = sorted(failed["by_action"].items(), key=lambda item: item[1]["count"], reverse=True)
    actions = [(escape(action), str(failure["count"]), escape(failure["error"])) for action, failure in by_count]
    return (
        "<h3>By day</h3>"
        + render_html_table(
            ("day", "failed actions", f"against the {TICKS_OF_A_DAY} ticks of a day"), days, "no tick action failed"
        )
        + "<h3>By action</h3>"
        + render_html_table(("action", "failed", "most frequent error"), actions, "no tick action failed")
    )


def _render_volume(overview: dict) -> str:
    period = _name_period(overview)
    counts = (
        ("events", sum(overview["events"].values())),
        ("runs finished", _count_runs(overview)),
        ("segments finished", sum(overview["segments"]["outcomes"].values())),
        ("waves started", sum(len(waves) for waves in overview["waves_started"].values())),
        ("failed tick actions", sum(overview["failed_actions"]["by_day"].values())),
    )
    tiles = "".join(
        render_stat_tile(StatTile(label=label, value=str(count), perimeter=period)) for label, count in counts
    )
    return f"{tiles}<h3>Waves started by month</h3>{_render_months(overview)}"


def _link_comparison(day: str, first_day: str, last_day: str) -> str:
    if first_day >= day:
        return ABSENT
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


def _render_halt(pause: dict) -> tuple[str, ...]:
    if pause["resumed_at"] is None:
        return (escape(pause["halted_at"]), "still halted", ABSENT)
    minutes = pause["duration_ms"] // MILLISECONDS_PER_MINUTE
    return (escape(pause["halted_at"]), escape(pause["resumed_at"]), str(minutes))


def _render_wave(document: dict) -> str:
    ledger = document["ledger"]
    roles = [_render_steps(role, summary["runs"]) for role, summary in ledger["turns"]["by_role"].items()]
    halts = [_render_halt(halt) for halt in ledger["halts"]]
    return (
        f"<p>wave {escape(document['wave'])}</p>"
        f"{render_html_table(('role', *STEPS_HEADER), roles, 'no run finished')}"
        f"{render_html_table(('halted at', 'resumed at', 'minutes'), halts, 'no halt')}"
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
        *(f"{percentile} {_name_range(day_range)}" for day_range in ranges for percentile in ("p50", "p90")),
    )
    counts = ", ".join(escape(f"{day_range['runs']} runs from {_name_range(day_range)}") for day_range in ranges)
    too_small = "".join(
        f"<p>{escape(_name_range(day_range))} holds {day_range['runs']} runs, too small to compare:"
        f" a percentile over fewer than {MEASURED_RUNS_FOR_A_COMPARISON} runs is an estimate.</p>"
        for day_range in ranges
        if day_range["runs"] < MEASURED_RUNS_FOR_A_COMPARISON
    )
    return f"{too_small}<p>{counts}</p>{render_html_table(header, rows, 'no measure')}"


SECTIONS = (
    ("budgets", "Do the turn caps fit", _render_caps),
    ("budgets", "What a run takes", _render_procedures),
    ("overview", "What keeps failing", _render_failures),
    ("overview", "Volume", _render_volume),
    ("comparison", "Compare two periods", _render_comparison),
    ("wave", "Turns by role and halts of the wave", _render_wave),
)


def render_ledger_fragment(answers: dict[str, CommandAnswer]) -> str:
    return render_answer(answers["overview"], _render_coverage) + "".join(
        f"<section><h2>{heading}</h2>{render_answer(answers[name], render)}</section>"
        for name, heading, render in SECTIONS
        if name in answers
    )
