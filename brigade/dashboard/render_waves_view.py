from collections import Counter
from datetime import datetime, timedelta
from html import escape
from urllib.parse import quote, urlencode

from brigade.dashboard.format_span import format_span
from brigade.dashboard.render_answer import render_answer
from brigade.dashboard.render_block import Block, render_block
from brigade.dashboard.render_callout import render_callout
from brigade.dashboard.render_filter_chips import FilterChip, render_filter_chips
from brigade.dashboard.render_html_table import render_html_table
from brigade.dashboard.render_page_head import PageHead, render_page_head
from brigade.dashboard.render_segment_strip import Segment, render_segment_strip
from brigade.dashboard.render_stat_tile import StatTile, render_stat_tile
from brigade.dashboard.render_status_pill import render_status_pill
from brigade.dashboard.render_status_sentence import render_status_sentence
from brigade.dashboard.run_routed_command import CommandAnswer

LISTING = "document"
OVERVIEW = "overview"
EVERY_WAVE = "every"
WAVES_VIEW = "waves"
WAVE_STATES = ("open", "blocked", "parked", "ended")
EVERY_STATE = "All"
HEADER = ("wave", "state", "started", "lasted", "tasks", "rounds", "cost")
HEAD = PageHead(
    title="Waves",
    lede="A wave is a batch of ratified tasks brigade delivers unattended, one branch and one pull request per task.",
)
SHORT_DATE = "%m-%d %H:%MZ"
MILLISECONDS_PER_SECOND = 1000
OPEN = "open"
NO_WAVE = "no wave started"
NOTHING = "\u2013"
NOT_RECORDED = '<span class="muted">not recorded</span>'
LONG_WAVE = timedelta(days=1)
MANY_ROUNDS = 3
NO_ROUND = 0
NO_MONTH = "none"
RUNNING = "running"
PARKED = "parked"
BLOCKED = "blocked"
CLOSED = "closed"
CANCELLED = "cancelled"
MERGED = "merged"
QUEUED = "queued"
NEVER_STARTED = "never started"
ENDED_STATES = {"wave.closed": CLOSED, "wave.cancelled": CANCELLED}
LAST_WAVES = 12
SERVED_AGAIN = 3
SERVED_AGAIN_LEDE = "A task parked in a closed wave is served again by a later wave."
EXPLAINER = (
    "<p>The tick composes a wave by itself from the tasks that are ready, runs each task through build, checks and"
    " review, and merges it. A wave is <b>open</b> until each of its tasks is merged or parked.</p>"
    "<p>A wave that stops is either <b>blocked</b>, on the quota, and resumes by itself at the time shown, or"
    " <b>parked</b>, and waits for you. A task parked in a closed wave is served again by a later wave.</p>"
    "<p>Come here to see what is open, why a wave waits, and how the last ones ended. A wave that lasted over a"
    " day or took three rounds or more is flagged.</p>"
)


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
    never_started = sum(task["state"] is None for task in wave["task_states"])
    beside = [f"{count} {word}" for count, word in ((counts[PARKED], PARKED), (never_started, NEVER_STARTED)) if count]
    merged = " · ".join([f"{counts[MERGED]} of {len(wave['task_states'])} merged", *beside])
    return f'{strip} <span class="muted num">{merged}</span>'


def _show_start(wave: dict) -> str:
    return datetime.fromisoformat(wave["started_at"]).strftime(SHORT_DATE)


def _flag(shown: str) -> str:
    return f'<span class="flag">{shown}</span>'


def _show_lasted(wave: dict) -> str:
    if wave["ended_at"] is None:
        return OPEN
    lasted = datetime.fromisoformat(wave["ended_at"]) - datetime.fromisoformat(wave["started_at"])
    shown = format_span(round(lasted.total_seconds() * MILLISECONDS_PER_SECOND))
    return _flag(shown) if lasted > LONG_WAVE else shown


def _show_rounds(rounds: int) -> str:
    if rounds == NO_ROUND:
        return NOTHING
    return _flag(str(rounds)) if rounds >= MANY_ROUNDS else str(rounds)


def _show_cost(cost_usd: float | None) -> str:
    return NOT_RECORDED if cost_usd is None else f"at least {cost_usd:.2f} USD"


def _render_row(wave: dict) -> tuple[str, ...]:
    return (
        _render_link(wave["wave"]),
        render_status_pill(wave["state"]),
        _show_start(wave),
        _show_lasted(wave),
        _render_tasks(wave),
        _show_rounds(wave["rounds"]),
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
        f"{task} of {project} went through {count} waves"
        for (project, task), count in served.most_common()
        if count >= SERVED_AGAIN
    ]
    if not again:
        return ""
    callout = render_callout(PARKED, f"{'; '.join(again)}.")
    return render_block(Block(title="Tasks served by three waves or more", lede=SERVED_AGAIN_LEDE, body=callout))


def _address(state: str | None) -> str:
    return WAVES_VIEW if state is None else f"{WAVES_VIEW}?{urlencode({'state': state})}"


def _render_state_chips(waves: list[dict], chosen: str | None) -> str:
    states = Counter(wave["state"] for wave in waves)
    chips = [FilterChip(label=EVERY_STATE, view=_address(None), chosen=chosen is None, count=len(waves))]
    chips += [
        FilterChip(label=state.capitalize(), view=_address(state), chosen=chosen == state, count=states[state])
        for state in WAVE_STATES
    ]
    return render_filter_chips(chips)


def _render_view(listed: list[dict], waves: list[dict], waves_started: dict, state: str | None) -> str:
    states = Counter(_read_wave_state(wave) for wave in waves)
    sentence = f"Waves open: {_count_open(waves)}, parked: {states[PARKED]}, blocked: {states[BLOCKED]}."
    newest_first = sorted(listed, key=lambda wave: wave["started_at"], reverse=True)
    return (
        f"{render_page_head(HEAD)}{render_status_sentence(sentence)}"
        f'<details class="explainer"><summary>How to read this page</summary><div>{EXPLAINER}</div></details>'
        f"{_render_tiles(waves, states, waves_started)}{_render_state_chips(waves, state)}"
        f"{render_html_table(HEADER, [_render_row(wave) for wave in newest_first], NO_WAVE)}"
        f"{_render_served_again(waves)}"
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
