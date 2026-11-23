import json
import re
from collections import Counter
from datetime import date, timedelta
from html import escape
from itertools import count, takewhile

from brigade.dashboard.format_short_instant import format_short_instant
from brigade.dashboard.read_state_tone import read_state_tone
from brigade.dashboard.render_answer import render_answer
from brigade.dashboard.render_block import Block, render_block
from brigade.dashboard.render_callout import render_callout
from brigade.dashboard.render_cap_bar import CapBar, render_cap_bar
from brigade.dashboard.render_cap_history import render_cap_history
from brigade.dashboard.render_field import render_field
from brigade.dashboard.render_html_table import render_html_table
from brigade.dashboard.render_legend import LegendItem, render_legend
from brigade.dashboard.render_page_head import PageHead, render_page_head
from brigade.dashboard.render_stat_tile import StatTile, render_stat_tile
from brigade.dashboard.render_svg_bar import SvgBar, render_svg_bar
from brigade.dashboard.run_routed_command import CommandAnswer

ABSENT = "-"
MILLISECONDS_PER_MINUTE = 60000
STEPS_HEADER = ("runs", "p50", "p90")
MEASURE_HEADER = "measure"
MEASURE_MARKS = {True: "estimate", False: "measured"}
MEASURED_SEGMENTS_FOR_A_MEASUREMENT = 5
MEASURED_RUNS_FOR_A_COMPARISON = 5
TICKS_OF_A_DAY = 288
LOOPING_FAILURES = 250
CHART_HEIGHT = 50
COLUMN_STEP = 12
COLUMN_WIDTH = 10
COMMAND_WORD = re.compile(r"[a-z][a-z-]*")
EXIT_CODE = re.compile(r" exited (\d+)")
PERIMETER_STATE = ""
OVER_CAP_STATE = "turn_limit"
WITHIN_CAP_STATE = "done"
FAILED_ACTION_STATE = "failed"
RUN_STATE = "running"
UNMEASURED_OVERSHOOT = -1
CAPS_HEADER = (
    ("Role", ""),
    ("Shipped", "num"),
    ("Computed", "num"),
    ("Applied", "num"),
    ("Segments", "num"),
    ("Restarts", "num"),
    ("p90 of a segment, against the cap", ""),
    ("Trend", ""),
)
COMPARED_MEASURES = {
    "turns": "turns",
    "turns_to_first_edit": "turns to first edit",
    "oversized_output_turns": "oversized output turns",
}
DAY_LENGTH = len("YYYY-MM-DD")
PREVIOUS_DAY = timedelta(days=1)
DAYS_BEFORE_THE_LAST = timedelta(days=3)
RANGE_FORMAT = "YYYY-MM-DD..YYYY-MM-DD"
CHART_WIDTH = 720
LABEL_WIDTH = 150
TRACK_WIDTH = 500
TOP = 14
ROW_HEIGHT = 28
BAR_HEIGHT = 12
LABEL_OFFSET = 10
VALUE_GAP = 6
SOFT_OPACITY = "0.35"
LEAST_SCALE = 1
GRID_TOP = 6
AXIS_GAP = BAR_HEIGHT + 2
AXIS_LABEL_OFFSET = 18
AXIS_BOTTOM_MARGIN = 10
ROUND_STEP_FACTORS = (1, 2, 5)
DECIMAL_BASE = 10
MOST_MARKS_PAST_ZERO = 5
AXIS_UNIT = " turns"
CHART_LEGEND = (
    LegendItem(label="up to the median", state=RUN_STATE),
    LegendItem(label="up to the 90th percentile", state=RUN_STATE, soft=True),
)
WHAT_THE_LEDGER_IS = (
    (
        "Every event, a wave started, a pull request merged, a run finished, is one line appended to the ledger."
        " Nothing is rewritten, so the measures here can always be recomputed."
    ),
    (
        "A turn is one step of an agent. Each role has a turn cap per segment: too low and runs hand over again and"
        " again, too high and a lost run burns tokens. Brigade recomputes the cap of a role once it has measured"
        " enough segments."
    ),
    (
        "Come here after a few waves, to tune a cap, to compare two periods, or to find an action that fails at every"
        " tick."
    ),
)
HEAD = PageHead(
    title="Ledger",
    lede="The ledger is the journal of everything brigade did. This page turns it into measures:"
    " what a run takes, whether the turn caps fit, and what keeps failing.",
)


def _show(value: object) -> str:
    return ABSENT if value is None else escape(str(value))


def _render_explainer(paragraphs: tuple[str, ...]) -> str:
    body = "".join(f"<p>{escape(paragraph)}</p>" for paragraph in paragraphs)
    return f'<details class="explainer"><summary>How to read this page</summary><div>{body}</div></details>'


def _render_cell(tag: str, kind: str, content: str) -> str:
    named = f' class="{kind}"' if kind else ""
    return f"<{tag}{named}>{content}</{tag}>"


def _render_steps(name: str, runs: dict) -> tuple[str, ...]:
    return (escape(name), str(runs["measured"]), _show(runs["p50"]), _show(runs["p90"]))


def _measure_overshoot(budget: dict) -> float:
    if budget["segment_p90"] is None:
        return UNMEASURED_OVERSHOOT
    return budget["segment_p90"] / budget["applied"]


def _render_cap_fit(role: str, budget: dict) -> str:
    p90 = budget["segment_p90"]
    if p90 is None:
        return "no segment measured"
    applied = budget["applied"]
    bar = CapBar(
        label=f"segment p90 {p90} of {role} against its cap of {applied}",
        state=OVER_CAP_STATE if p90 > applied else WITHIN_CAP_STATE,
        value=p90,
        cap=applied,
    )
    estimate = " · estimate" if budget["segments"] < MEASURED_SEGMENTS_FOR_A_MEASUREMENT else ""
    return f"{render_cap_bar(bar)}{p90} · {round(100 * p90 / applied)} % of the cap{estimate}"


def _render_role(role: str, budget: dict) -> str:
    counts = (budget[name] for name in ("shipped", "computed", "applied", "segments", "restarts"))
    cells = (
        _render_cell("td", "mono", escape(role)),
        *(_render_cell("td", "num", _show(count)) for count in counts),
        _render_cell("td", "", _render_cap_fit(role, budget)),
        _render_cell("td", "", ABSENT),
    )
    return f"<tr>{''.join(cells)}</tr>"


def _render_caps(document: dict) -> str:
    by_overshoot = sorted(document["roles"].items(), key=lambda item: _measure_overshoot(item[1]), reverse=True)
    header = "".join(_render_cell("th", kind, name) for name, kind in CAPS_HEADER)
    rows = "".join(_render_role(role, budget) for role, budget in by_overshoot)
    histories = "".join(render_cap_history(role, budget) for role, budget in document["roles"].items())
    return (
        f'<div class="panel scroll"><table><thead><tr>{header}</tr></thead><tbody>{rows}</tbody></table></div>'
        '<div class="block-head"><h3>Applied cap over time</h3><p>One step line per role, each change marked.</p></div>'
        f'<figure class="panel pad chart"><div class="multiples">{histories}</div></figure>'
    )


def _describe_caps(document: dict) -> str:
    return f"The last {document['last']} runs of each procedure. A cap fits when 9 segments in 10 end under it."


def _render_procedure_bars(index: int, name: str, runs: dict, scale: float) -> str:
    top = TOP + ROW_HEIGHT * index
    p90_width = runs["p90"] * scale
    title = f"{name}: p50 {runs['p50']}, p90 {runs['p90']} turns"
    return (
        f"<g><title>{escape(title)}</title>"
        f'<text class="g-label" x="0" y="{top + LABEL_OFFSET}">{escape(name)}</text>'
        f'<rect class="bar-fill tone-work" x="{LABEL_WIDTH}" y="{top}" width="{p90_width:g}"'
        f' height="{BAR_HEIGHT}" fill-opacity="{SOFT_OPACITY}"></rect>'
        f'<rect class="bar-fill tone-work" x="{LABEL_WIDTH}" y="{top}" width="{runs["p50"] * scale:g}"'
        f' height="{BAR_HEIGHT}"></rect>'
        f'<text class="g-text" x="{LABEL_WIDTH + p90_width + VALUE_GAP:g}" y="{top + LABEL_OFFSET}">'
        f"{runs['p90']}</text></g>"
    )


def _step_axis(longest: int) -> int:
    steps = (factor * DECIMAL_BASE**power for power in count() for factor in ROUND_STEP_FACTORS)
    return next(step for step in steps if longest // step <= MOST_MARKS_PAST_ZERO)


def _place_mark(mark: int, scale: float) -> str:
    return f"{round(LABEL_WIDTH + mark * scale, 1):g}"


def _render_grid_line(mark: int, scale: float, bottom: int) -> str:
    x = _place_mark(mark, scale)
    return f'<line class="g-grid" x1="{x}" y1="{GRID_TOP}" x2="{x}" y2="{bottom}"></line>'


def _render_mark_label(mark: int, label: str, scale: float, baseline: int) -> str:
    return f'<text class="g-text" x="{_place_mark(mark, scale)}" y="{baseline}" text-anchor="middle">{label}</text>'


def _render_chart(document: dict) -> str:
    measured = [(name, summary["runs"]) for name, summary in document["procedures"].items() if summary["runs"]["p90"]]
    longest = max([runs["p90"] for _, runs in measured] + [LEAST_SCALE])
    scale = TRACK_WIDTH / longest
    bars = "".join(_render_procedure_bars(index, name, runs, scale) for index, (name, runs) in enumerate(measured))
    bottom = TOP + ROW_HEIGHT * len(measured) - AXIS_GAP
    baseline = bottom + AXIS_LABEL_OFFSET
    marks = list(range(0, longest + 1, _step_axis(longest)))
    grid = "".join(_render_grid_line(mark, scale, bottom) for mark in marks)
    labels = [str(mark) for mark in marks[:-1]] + [f"{marks[-1]}{AXIS_UNIT}"]
    axis = "".join(_render_mark_label(mark, label, scale, baseline) for mark, label in zip(marks, labels, strict=True))
    return (
        f'<figure class="panel pad chart"><svg viewBox="0 0 {CHART_WIDTH} {baseline + AXIS_BOTTOM_MARGIN}" role="img"'
        f' aria-label="Turns by procedure, p50 and p90">{grid}{bars}{axis}</svg>{render_legend(CHART_LEGEND)}</figure>'
    )


def _render_procedures(document: dict) -> str:
    rows = [
        (*_render_steps(name, summary["runs"]), MEASURE_MARKS[summary["estimate"]])
        for name, summary in document["procedures"].items()
    ]
    return _render_chart(document) + render_html_table(
        ("procedure", *STEPS_HEADER, MEASURE_HEADER), rows, "no run finished"
    )


def _name_period(overview: dict) -> str:
    if overview["first"] is None:
        return "in an empty ledger"
    return f"from {format_short_instant(overview['first'])} to {format_short_instant(overview['last'])}"


def _count_runs(overview: dict) -> int:
    return sum(overview["runs"]["outcomes"].values())


def _render_coverage(overview: dict) -> str:
    return render_callout(
        PERIMETER_STATE,
        f"The measures cover {_count_runs(overview)} runs finished {_name_period(overview)};"
        f" {len(overview['skipped'])} lines of the ledger skipped, counted in no figure.",
    )


def _name_error(error: str) -> str:
    words = list(takewhile(COMMAND_WORD.fullmatch, error.split(" ")))
    exited = EXIT_CODE.search(error)
    if not words or exited is None:
        return error
    return f"{' '.join(words)} exited {exited.group(1)}"


def _render_day_column(index: int, day: str, count: int, most: int) -> str:
    height = CHART_HEIGHT * count / most
    return (
        f'<rect class="bar-fill tone-{read_state_tone(FAILED_ACTION_STATE)}" x="{index * COLUMN_STEP + 1}"'
        f' y="{CHART_HEIGHT - height:g}" width="{COLUMN_WIDTH}" height="{height:g}">'
        f"<title>{escape(day)}: {count}</title></rect>"
    )


def _render_days(by_day: dict[str, int]) -> str:
    if not by_day:
        return "<p>No tick action failed.</p>"
    most = max(by_day.values())
    columns = "".join(_render_day_column(index, day, count, most) for index, (day, count) in enumerate(by_day.items()))
    days = list(by_day)
    looping = [day for day, count in by_day.items() if count > LOOPING_FAILURES]
    reading = (
        f" It happened on {len(looping)} days: {', '.join(looping)}."
        if looping
        else f" No day passed {LOOPING_FAILURES}."
    )
    return (
        f'<figure class="day-chart"><svg viewBox="0 0 {len(days) * COLUMN_STEP} {CHART_HEIGHT}" role="img"'
        f' aria-label="failed tick actions by day, at most {most} in a day">{columns}</svg>'
        f"<figcaption>{escape(days[0])} to {escape(days[-1])} · at most {most} in a day</figcaption></figure>"
        f"<p>A day holds {TICKS_OF_A_DAY} ticks: over {LOOPING_FAILURES} failures in a day is one action refused at"
        f" nearly every tick.{reading}</p>"
    )


def _render_failed_action(action: str, failure: dict, total: int) -> tuple[str, ...]:
    share = SvgBar(
        label=f"{round(100 * failure['count'] / total)} percent of the failed actions",
        state=FAILED_ACTION_STATE,
        value=failure["count"],
        total=total,
    )
    return (escape(action), str(failure["count"]), render_svg_bar(share), escape(_name_error(failure["error"])))


def _render_failures(overview: dict) -> str:
    failed = overview["failed_actions"]
    total = sum(failure["count"] for failure in failed["by_action"].values())
    by_count = sorted(failed["by_action"].items(), key=lambda item: item[1]["count"], reverse=True)
    actions = [_render_failed_action(action, failure, total) for action, failure in by_count]
    return (
        "<h3>By day</h3>"
        + _render_days(failed["by_day"])
        + "<h3>By action</h3>"
        + render_html_table(("action", "failed", "share", "most frequent error"), actions, "no tick action failed")
    )


def _describe_failures(overview: dict) -> str:
    return f"The {sum(overview['failed_actions']['by_day'].values())} tick actions that failed, by day and by action."


def _per(count: int, base: int, noun: str) -> str:
    return f"{count / base:.1f} per {noun}" if base else f"no {noun} to count against"


def _render_volume(overview: dict) -> str:
    events = Counter(overview["events"])
    tiles = (
        StatTile(
            "waves started",
            str(events["wave.started"]),
            f"{events['wave.closed']} closed · {events['wave.cancelled']} cancelled",
        ),
        StatTile("pull requests merged", str(events["pr.merged"]), f"of {events['task.pr_opened']} opened by tasks"),
        StatTile(
            "review verdicts",
            str(events["task.verdict"]),
            _per(events["task.verdict"], events["pr.merged"], "merged pull request"),
        ),
        StatTile(
            "tasks parked", str(events["task.parked"]), _per(events["task.parked"], events["wave.started"], "wave")
        ),
        StatTile(
            "orders started",
            str(events["order.started"]),
            f"{events['order.done']} done · {events['order.parked']} parked",
        ),
        StatTile("signals recorded", str(events["inbox.recorded"]), f"{events['inbox.dismissed']} dismissals"),
    )
    return f'<div class="stat-tiles">{"".join(render_stat_tile(tile) for tile in tiles)}</div>'


def _describe_volume(overview: dict) -> str:
    if overview["first"] is None:
        return "What the ledger counts: nothing yet."
    return f"What the ledger counts since {overview['first'][:DAY_LENGTH]}."


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


def _suggest_ranges(overview: CommandAnswer) -> tuple[str, str]:
    last = json.loads(overview.document).get("last")
    if last is None:
        return (RANGE_FORMAT, RANGE_FORMAT)
    last_day = date.fromisoformat(last[:DAY_LENGTH])
    before = (last_day - DAYS_BEFORE_THE_LAST, last_day - PREVIOUS_DAY)
    return (f"{before[0]}..{before[1]}", f"{last_day}..{last_day}")


def _render_range_input(label: str, name: str, placeholder: str) -> str:
    control = f'<input id="{name}" name="range" data-pauses-poll placeholder="{escape(placeholder)}">'
    return render_field(label, name, control)


def _render_compare_form(answers: dict[str, CommandAnswer]) -> str:
    before, after = _suggest_ranges(answers["overview"])
    return (
        '<form class="filters" data-view="ledger">'
        f"{_render_range_input('Before', 'ledger-before', before)}"
        f"{_render_range_input('After', 'ledger-after', after)}"
        '<button class="btn" type="submit">Compare</button></form>'
    )


def _render_compare(answers: dict[str, CommandAnswer]) -> str:
    compared = render_answer(answers["comparison"], _render_comparison) if "comparison" in answers else ""
    return render_block(
        Block(
            title="Compare two periods",
            lede="Runs finished in each range of days, UTC.",
            body=_render_compare_form(answers) + compared,
        )
    )


def _render_answered_block(answer: CommandAnswer, title: str, describe, render) -> str:
    return render_answer(
        answer, lambda document: render_block(Block(title=title, lede=describe(document), body=render(document)))
    )


def _render_wave_section(answers: dict[str, CommandAnswer]) -> str:
    if "wave" not in answers:
        return ""
    body = render_answer(answers["wave"], _render_wave)
    return f"<section><h2>Turns by role and halts of the wave</h2>{body}</section>"


def render_ledger_fragment(answers: dict[str, CommandAnswer]) -> str:
    budgets = answers["budgets"]
    overview = answers["overview"]
    return (
        render_page_head(HEAD)
        + _render_explainer(WHAT_THE_LEDGER_IS)
        + render_answer(overview, _render_coverage)
        + _render_answered_block(budgets, "Do the turn caps fit?", _describe_caps, _render_caps)
        + _render_answered_block(
            budgets,
            "What a run takes",
            lambda _: "Turns of a whole run, by procedure: the median, and the 90th percentile.",
            _render_procedures,
        )
        + _render_answered_block(overview, "What keeps failing", _describe_failures, _render_failures)
        + _render_answered_block(overview, "Volume", _describe_volume, _render_volume)
        + _render_compare(answers)
        + _render_wave_section(answers)
    )
