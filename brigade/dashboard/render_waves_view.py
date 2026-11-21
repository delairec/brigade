from collections import Counter
from datetime import datetime
from html import escape
from urllib.parse import quote

from brigade.dashboard.format_span import format_span
from brigade.dashboard.render_answer import render_answer
from brigade.dashboard.render_html_table import render_html_table
from brigade.dashboard.render_page_head import PageHead, render_page_head
from brigade.dashboard.render_segment_strip import Segment, render_segment_strip
from brigade.dashboard.render_stat_tile import StatTile, render_stat_tile
from brigade.dashboard.render_status_pill import render_status_pill
from brigade.dashboard.render_status_sentence import render_status_sentence
from brigade.dashboard.run_routed_command import CommandAnswer

LISTING = "document"
OVERVIEW = "overview"
HEADER = ("wave", "state", "started", "lasted", "tasks", "rounds", "cost")
HEAD = PageHead(
    title="Waves",
    lede="A wave is a batch of ratified tasks brigade delivers unattended, one branch and one pull request per task.",
)
SHORT_DATE = "%m-%d %H:%MZ"
MILLISECONDS_PER_SECOND = 1000
OPEN = "open"
NO_WAVE = "no wave started"
ABSENT = "-"
NO_MONTH = "none"
RUNNING = "running"
PARKED = "parked"
BLOCKED = "blocked"
CLOSED = "closed"
CANCELLED = "cancelled"
MERGED = "merged"
QUEUED = "queued"
ENDED_STATES = {"wave.closed": CLOSED, "wave.cancelled": CANCELLED}
LAST_WAVES = 12
SERVED_AGAIN = 3


def _read_wave_state(wave: dict) -> str:
    if wave["ended_by"] is not None:
        return ENDED_STATES[wave["ended_by"]]
    halt = wave["halt"]
    if halt is not None:
        return PARKED if halt["resume_at"] is None else BLOCKED
    return RUNNING


def _render_link(name: str) -> str:
    return f'<a href="#waves/{escape(quote(name, safe=""))}">{escape(name)}</a>'


def _render_tasks(wave: dict) -> str:
    counts = Counter(task["state"] or QUEUED for task in wave["task_states"])
    segments = [Segment(label=f"{count} {state}", state=state, length=count) for state, count in counts.items()]
    strip = render_segment_strip(f"{len(wave['task_states'])} tasks", segments)
    return f'{strip} <span class="muted num">{counts[MERGED]} of {len(wave["task_states"])} merged</span>'


def _show_start(wave: dict) -> str:
    return datetime.fromisoformat(wave["started_at"]).strftime(SHORT_DATE)


def _show_lasted(wave: dict) -> str:
    if wave["ended_at"] is None:
        return OPEN
    lasted = datetime.fromisoformat(wave["ended_at"]) - datetime.fromisoformat(wave["started_at"])
    return format_span(round(lasted.total_seconds() * MILLISECONDS_PER_SECOND))


def _show_cost(cost_usd: float | None) -> str:
    return ABSENT if cost_usd is None else f"at least {cost_usd:.2f} USD"


def _render_row(wave: dict) -> tuple[str, ...]:
    return (
        _render_link(wave["wave"]),
        render_status_pill(_read_wave_state(wave)),
        _show_start(wave),
        _show_lasted(wave),
        _render_tasks(wave),
        str(wave["rounds"]),
        _show_cost(wave["cost_usd"]),
    )


def _count_open(waves: list[dict]) -> int:
    return sum(wave["ended_at"] is None for wave in waves)


def _count_by_month(waves: list[dict], waves_started: dict) -> str:
    listed = {wave["wave"] for wave in waves}
    months = [f"{month} {len(listed.intersection(started))}" for month, started in waves_started.items()]
    return f"by month: {', '.join(months) or NO_MONTH}"


def _count_merged(waves: list[dict]) -> StatTile:
    last = sorted(waves, key=lambda wave: wave["started_at"], reverse=True)[:LAST_WAVES]
    merged = [sum(task["state"] == MERGED for task in wave["task_states"]) for wave in last]
    served = sum(len(wave["task_states"]) for wave in last)
    return StatTile(
        label="tasks merged",
        value=f"{sum(merged)} of {served}",
        perimeter=f"over the last {LAST_WAVES} waves, {merged.count(0)} merged nothing",
    )


def _render_tiles(waves: list[dict], states: Counter, waves_started: dict) -> str:
    tiles = [
        StatTile(
            label="open now",
            value=str(_count_open(waves)),
            perimeter=f"{states[PARKED]} parked, {states[BLOCKED]} blocked",
        ),
        StatTile(label="started", value=str(len(waves)), perimeter=_count_by_month(waves, waves_started)),
        StatTile(label=CLOSED, value=str(states[CLOSED]), perimeter=f"{states[CANCELLED]} cancelled"),
        _count_merged(waves),
    ]
    return f'<div class="stat-tiles">{"".join(render_stat_tile(tile) for tile in tiles)}</div>'


def _render_served_again(waves: list[dict]) -> str:
    served = Counter((wave["project"], task["task"]) for wave in waves for task in wave["task_states"])
    again = [
        f"<li>{escape(task)} of {escape(project)}, {count} waves</li>"
        for (project, task), count in served.most_common()
        if count >= SERVED_AGAIN
    ]
    if not again:
        return ""
    return f"<section><h2>Tasks served by three waves or more</h2><ul>{''.join(again)}</ul></section>"


def _render_view(waves: list[dict], waves_started: dict) -> str:
    states = Counter(_read_wave_state(wave) for wave in waves)
    sentence = f"Waves open: {_count_open(waves)}, parked: {states[PARKED]}, blocked: {states[BLOCKED]}."
    newest_first = sorted(waves, key=lambda wave: wave["started_at"], reverse=True)
    return (
        f"{render_page_head(HEAD)}{render_status_sentence(sentence)}{_render_tiles(waves, states, waves_started)}"
        f"{render_html_table(HEADER, [_render_row(wave) for wave in newest_first], NO_WAVE)}"
        f"{_render_served_again(waves)}"
    )


def render_waves_view(answers: dict[str, CommandAnswer]) -> str:
    return render_answer(
        answers[OVERVIEW],
        lambda overview: render_answer(
            answers[LISTING], lambda listing: _render_view(listing["waves"], overview["waves_started"])
        ),
    )
