from dataclasses import dataclass
from html import escape
from urllib.parse import quote

from brigade.dashboard.render_callout import render_callout
from brigade.dashboard.render_empty_state import render_empty_state
from brigade.dashboard.render_html_table import render_html_table
from brigade.dashboard.render_stat_tile import StatTile, render_stat_tile
from brigade.dashboard.render_status_pill import render_status_pill
from brigade.dashboard.render_status_sentence import render_status_sentence
from brigade.dashboard.render_svg_bar import SvgBar, render_svg_bar
from brigade.runs.format_duration import format_duration

ABSENT = "-"
HANDED_OVER = "handed_over"
HANDOVER_TYPE = "HANDOVER"
NEXT_FIELD = "NEXT"
SEGMENT_HEADER = ("segment", "outcome", "turns", "start", "duration", "cost")
NOTE_HEADER = ("noted", "carried by", "note")
TASK_RUN_HEADER = ("run", "finished", "slot", "outcome", "turns", "duration", "cost")
PENDING_NOTE = "pending"
NO_MESSAGE = "the run left no message"
NO_WAVE_COST = "no cost of a wave to share"
NO_SEGMENT = "no segment"
NO_NOTE = "No note was handed to this run."
WHAT_WOULD_NOTE = "brigade run note hands a note to the next segment of a run."
NO_TURNS = 0
NO_DURATION = 0
LIVE = "running"
DEAD = "dead"


@dataclass(frozen=True)
class RunPage:
    shown: dict
    budgets: dict | None
    task_runs: dict | None
    wave: dict | None


def _show(value: object) -> str:
    return ABSENT if value is None else escape(str(value))


def _show_cost(cost: float | None) -> str:
    return ABSENT if cost is None else f"${cost:.2f}"


def _show_duration(duration_ms: int | None) -> str:
    return ABSENT if duration_ms is None else format_duration(duration_ms)


@dataclass(frozen=True)
class PageReading:
    run: dict
    segments: list[dict]
    cap: int | None


def _read_page(page: RunPage) -> PageReading:
    run = page.shown["run"]
    roles = {} if page.budgets is None else page.budgets["roles"]
    budget = roles.get(run["role"])
    return PageReading(run=run, segments=page.shown["segments"], cap=None if budget is None else budget["applied"])


def _describe_standing(reading: PageReading) -> str:
    run = reading.run
    who = f"{run['procedure']} by {run['role']}"
    if run["state"] == LIVE:
        return f"{who} is running, in its segment {len(reading.segments)}."
    if run["state"] == DEAD:
        return f"{who} died in its segment {len(reading.segments)} without a result."
    return f"{who} finished on {run['outcome']}."


def _show_state(run: dict) -> str:
    return run["outcome"] or run["state"]


def _read_next_entries(progress: dict | None) -> list[str]:
    entities = [] if progress is None or progress["entities"] is None else progress["entities"]
    return [field["value"] for entity in entities for field in entity["fields"] if field["name"] == NEXT_FIELD]


def _render_next(page: RunPage) -> str:
    entries = _read_next_entries(page.shown["progress"])
    if not entries:
        return ""
    return render_callout(_show_state(page.shown["run"]), f"Left for its next segment: {entries[-1]}")


def _describe_cost(reading: PageReading, wave: dict | None) -> StatTile:
    costs = [segment["cost_usd"] for segment in reading.segments]
    cost = sum(value for value in costs if value is not None)
    floor = "at least " if None in costs else ""
    wave_cost = None if wave is None else wave["ledger"]["cost_usd"]
    if not wave_cost:
        perimeter = NO_WAVE_COST
    else:
        perimeter = f"{cost / wave_cost:.0%} of the ${wave_cost:.2f} of wave {reading.run['wave']}"
    return StatTile(label="cost", value=f"{floor}${cost:.2f}", perimeter=perimeter)


def _describe_cap(reading: PageReading) -> str:
    if reading.cap is None:
        return f"no cap recorded for {reading.run['role']}"
    return f"against the cap of {reading.cap} turns a segment of {reading.run['role']}"


def _render_tiles(reading: PageReading, page: RunPage) -> str:
    segments = reading.segments
    handovers = sum(segment["outcome"] == HANDED_OVER for segment in segments)
    turns = sum(segment["turns"] or NO_TURNS for segment in segments)
    duration_ms = sum(segment["duration_ms"] or NO_DURATION for segment in segments)
    tiles = [
        StatTile(label="outcome", value=_show_state(reading.run), perimeter=reading.run["message"] or NO_MESSAGE),
        StatTile(label="segments", value=str(len(segments)), perimeter=f"handovers: {handovers}"),
        StatTile(label="turns", value=str(turns), perimeter=_describe_cap(reading)),
        StatTile(label="run time", value=format_duration(duration_ms), perimeter="over the segments that ended"),
        _describe_cost(reading, page.wave),
    ]
    return f'<div class="stat-tiles">{"".join(render_stat_tile(tile) for tile in tiles)}</div>'


def _render_turns(segment: dict, cap: int | None) -> str:
    turns = segment["turns"]
    if turns is None:
        return ABSENT
    if cap is None:
        return str(turns)
    bar = render_svg_bar(SvgBar(label=f"{turns} of {cap} turns", state=segment["outcome"], value=turns, total=cap))
    over = ", over its cap" if turns > cap else ""
    return f"{bar}{turns}/{cap}{over}"


def _render_segment(segment: dict, reading: PageReading) -> tuple[str, ...]:
    return (
        str(segment["segment"]),
        render_status_pill(segment["outcome"] or reading.run["state"]),
        _render_turns(segment, reading.cap),
        _show(segment["started_at"]),
        _show_duration(segment["duration_ms"]),
        _show_cost(segment["cost_usd"]),
    )


def _render_section(heading: str, body: str) -> str:
    return f"<section><h3>{escape(heading)}</h3>{body}</section>"


def _render_entity(entity: dict) -> str:
    fields = "".join(f"<dd>{escape(field['name'])}: {escape(field['value'])}</dd>" for field in entity["fields"])
    return f"<dt>{escape(entity['type'])} {escape(entity['name'])}</dt>{fields}"


def _cut_by_segment(entities: list[dict]) -> list[list[dict]]:
    cuts = [[]]
    for entity in entities:
        cuts[-1].append(entity)
        if entity["type"] == HANDOVER_TYPE:
            cuts.append([])
    return [cut for cut in cuts if cut]


def _render_progress(progress: dict | None) -> str:
    if progress is None:
        return ""
    if progress["entities"] is None:
        return _render_section("Progress", f"<pre>{escape(progress['text'])}</pre>")
    cuts = _cut_by_segment(progress["entities"])
    body = "".join(
        f"<h4>Segment {number}</h4><dl>{''.join(_render_entity(entity) for entity in cut)}</dl>"
        for number, cut in enumerate(cuts, start=1)
    )
    return _render_section("Progress", body)


def _render_note(note: dict) -> tuple[str, ...]:
    carrier = PENDING_NOTE if note["segment"] is None else f"segment {note['segment']}"
    return escape(note["at"]), carrier, escape(note["text"])


def _render_notes(notes: list[dict]) -> str:
    if not notes:
        return _render_section("Notes", render_empty_state(NO_NOTE, WHAT_WOULD_NOTE))
    return _render_section("Notes", render_html_table(NOTE_HEADER, [_render_note(note) for note in notes], NO_NOTE))


def _render_task_run(run: dict) -> tuple[str, ...]:
    return (
        f'<a href="#runs/{escape(quote(run["run"], safe=""))}">{escape(run["run"])}</a>',
        escape(run["finished_at"]),
        escape(run["slot"]),
        render_status_pill(run["outcome"]),
        _show(run["turns"]),
        _show_duration(run["duration_ms"]),
        _show_cost(run["cost_usd"]),
    )


def _render_task_runs(run: dict, task_runs: dict | None) -> str:
    task = run["task"]
    if task is None:
        return ""
    listed = [] if task_runs is None else task_runs["runs"]
    others = [_render_task_run(other) for other in listed if other["run"] != run["run"]]
    heading = f"Other runs of task {task}"
    if not others:
        empty = render_empty_state(
            f"No other run of task {task} has finished.", "A run of the task appears here once it finishes."
        )
        return _render_section(heading, empty)
    return _render_section(heading, render_html_table(TASK_RUN_HEADER, others, heading))


def _render_arguments(arguments: dict) -> str:
    fields = "".join(f"<dt>{escape(name)}</dt><dd>{escape(str(value))}</dd>" for name, value in arguments.items())
    return _render_section("Arguments", f"<dl>{fields}</dl>")


def render_run_fragment(page: RunPage) -> str:
    reading = _read_page(page)
    shown = page.shown
    segments = [_render_segment(segment, reading) for segment in reading.segments]
    return (
        f"<h2>Run {escape(reading.run['run'])}</h2>"
        + render_status_sentence(_describe_standing(reading))
        + _render_next(page)
        + _render_tiles(reading, page)
        + _render_section("Segments", render_html_table(SEGMENT_HEADER, segments, NO_SEGMENT))
        + _render_progress(shown["progress"])
        + _render_notes(shown["notes"])
        + _render_task_runs(reading.run, page.task_runs)
        + _render_arguments(shown["arguments"])
    )
