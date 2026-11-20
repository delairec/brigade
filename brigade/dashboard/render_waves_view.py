from collections import Counter
from html import escape
from urllib.parse import quote, urlencode

from brigade.dashboard.render_answer import render_answer
from brigade.dashboard.render_filter_chips import FilterChip, render_filter_chips
from brigade.dashboard.render_html_table import render_html_table
from brigade.dashboard.render_segment_strip import Segment, render_segment_strip
from brigade.dashboard.render_stat_tile import StatTile, render_stat_tile
from brigade.dashboard.render_status_pill import render_status_pill
from brigade.dashboard.render_status_sentence import render_status_sentence
from brigade.dashboard.run_routed_command import CommandAnswer

LISTING = "document"
OVERVIEW = "overview"
EVERY_WAVE = "every"
HEADER = ("wave", "state", "tasks", "started", "ended", "rounds", "cost")
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
WAVES_VIEW = "waves"
WAVE_STATES = ("open", "blocked", "parked", "ended")
EVERY_STATE = "every state"
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
    return render_segment_strip(f"{len(wave['task_states'])} tasks", segments)


def _show_cost(cost_usd: float | None) -> str:
    return ABSENT if cost_usd is None else f"at least {cost_usd:.2f} USD"


def _render_row(wave: dict) -> tuple[str, ...]:
    return (
        _render_link(wave["wave"]),
        render_status_pill(wave["state"]),
        _render_tasks(wave),
        escape(wave["started_at"]),
        escape(wave["ended_at"] or ABSENT),
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


def _address(state: str | None) -> str:
    return WAVES_VIEW if state is None else f"{WAVES_VIEW}?{urlencode({'state': state})}"


def _render_state_chips(chosen: str | None) -> str:
    chips = [FilterChip(label=EVERY_STATE, view=_address(None), chosen=chosen is None)]
    chips += [FilterChip(label=state, view=_address(state), chosen=chosen == state) for state in WAVE_STATES]
    return render_filter_chips(chips)


def _render_view(listed: list[dict], waves: list[dict], waves_started: dict, state: str | None) -> str:
    states = Counter(_read_wave_state(wave) for wave in waves)
    sentence = f"Waves open: {_count_open(waves)}, parked: {states[PARKED]}, blocked: {states[BLOCKED]}."
    return (
        f"{render_status_sentence(sentence)}{_render_tiles(waves, states, waves_started)}{_render_state_chips(state)}"
        f"{render_html_table(HEADER, [_render_row(wave) for wave in listed], NO_WAVE)}{_render_served_again(waves)}"
    )


def render_waves_view(answers: dict[str, CommandAnswer], state: str | None) -> str:
    return render_answer(
        answers[OVERVIEW],
        lambda overview: render_answer(
            answers[LISTING],
            lambda listing: render_answer(
                answers.get(EVERY_WAVE, answers[LISTING]),
                lambda every: _render_view(listing["waves"], every["waves"], overview["waves_started"], state),
            ),
        ),
    )
