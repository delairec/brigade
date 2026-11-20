from collections import Counter
from dataclasses import dataclass, replace
from html import escape
from urllib.parse import quote, urlencode

from brigade.dashboard.read_state_tone import read_state_tone
from brigade.dashboard.render_empty_state import render_empty_state
from brigade.dashboard.render_explainer import render_explainer
from brigade.dashboard.render_filter_chips import FilterChip, render_filter_chips
from brigade.dashboard.render_html_table import render_html_table
from brigade.dashboard.render_stat_tile import StatTile, render_stat_tile
from brigade.dashboard.render_status_pill import render_status_pill
from brigade.dashboard.render_status_sentence import render_status_sentence

RUNS_VIEW = "runs"
HEADER = ("run", "procedure", "task", "wave", "state", "start")
ABSENT = "-"
RUN_STATES = ("running", "finished", "dead")
LIVE = "running"
FINISHED = "finished"
DEAD = "dead"
LIMIT_TONE = "limit"
WHAT_A_RUN_IS = (
    "A run is one procedure a role carries out through a client, for a task of a wave or on its own. It runs in"
    " segments: a segment is one session of the client, and a segment that reaches the cap of its role hands over"
    " to the next through the progress of the run."
)
WHAT_THE_LIST_IS_FOR = (
    "Read the dead runs and the runs a limit cut first: they delivered nothing. Open a run to see where it stands"
    " and what it left for its next segment."
)
NO_RUN_MATCHES = "No run matches these filters."
WHAT_WOULD_FILL = "A run appears here once the tick or brigade run starts a procedure."


@dataclass(frozen=True)
class RunFilters:
    state: str | None
    wave: str | None
    task: str | None


def _address(filters: RunFilters) -> str:
    chosen = {name: value for name, value in vars(filters).items() if value is not None}
    return f"{RUNS_VIEW}?{urlencode(chosen)}" if chosen else RUNS_VIEW


def _render_chips(filters: RunFilters, name: str, everything: str, values: list[str]) -> str:
    chosen = getattr(filters, name)
    chips = [FilterChip(label=everything, view=_address(replace(filters, **{name: None})), chosen=chosen is None)]
    chips += [
        FilterChip(label=value, view=_address(replace(filters, **{name: value})), chosen=chosen == value)
        for value in values
    ]
    return render_filter_chips(chips)


def _list_values(runs: list[dict], field: str) -> list[str]:
    return sorted({run[field] for run in runs if run[field] is not None})


def _render_link(address: str, label: str) -> str:
    return f'<a href="#{escape(address)}">{escape(label)}</a>'


def _render_task(task: str | None) -> str:
    if task is None:
        return ABSENT
    return _render_link(_address(RunFilters(state=None, wave=None, task=task)), task)


def _render_wave(wave: str | None) -> str:
    if wave is None:
        return ABSENT
    return _render_link(f"waves/{quote(wave, safe='')}", wave)


def _show_state(run: dict) -> str:
    return run["outcome"] if run["state"] == FINISHED else run["state"]


def _render_row(run: dict) -> tuple[str, ...]:
    return (
        _render_link(f"{RUNS_VIEW}/{quote(run['run'], safe='')}", run["run"]),
        escape(run["procedure"]),
        _render_task(run["task"]),
        _render_wave(run["wave"]),
        render_status_pill(_show_state(run)),
        escape(run["started_at"]),
    )


def _render_section(heading: str, runs: list[dict]) -> str:
    if not runs:
        return ""
    table = render_html_table(HEADER, [_render_row(run) for run in runs], NO_RUN_MATCHES)
    return f"<section><h2>{escape(heading)}</h2>{table}</section>"


def _is_limit_cut(run: dict) -> bool:
    return run["state"] == FINISHED and read_state_tone(run["outcome"]) == LIMIT_TONE


def _render_sections(runs: list[dict]) -> str:
    if not runs:
        return render_empty_state(NO_RUN_MATCHES, WHAT_WOULD_FILL)
    dead = [run for run in runs if run["state"] == DEAD]
    cut = [run for run in runs if _is_limit_cut(run)]
    others = [run for run in runs if run not in dead and run not in cut]
    return (
        _render_section("Dead runs", dead)
        + _render_section("Runs cut by a limit", cut)
        + _render_section("Runs", others)
    )


def _render_tiles(runs: list[dict]) -> str:
    states = Counter(run["state"] for run in runs)
    outcomes = Counter(run["outcome"] for run in runs if run["state"] == FINISHED)
    tiles = [
        StatTile(label="live", value=str(states[LIVE]), perimeter="runs whose process is alive"),
        *(
            StatTile(label=outcome, value=str(count), perimeter="runs finished on this outcome")
            for outcome, count in sorted(outcomes.items())
        ),
        StatTile(label=DEAD, value=str(states[DEAD]), perimeter="runs whose process ended without a result"),
    ]
    return f'<div class="stat-tiles">{"".join(render_stat_tile(tile) for tile in tiles)}</div>'


def _describe_listing(runs: list[dict]) -> str:
    states = Counter(run["state"] for run in runs)
    return f"{len(runs)} runs listed: {states[LIVE]} live, {states[FINISHED]} finished, {states[DEAD]} dead."


def render_runs_fragment(document: dict, filters: RunFilters) -> str:
    runs = document["runs"]
    skipped = len(document["skipped"])
    return (
        render_status_sentence(_describe_listing(runs))
        + render_explainer(WHAT_A_RUN_IS, WHAT_THE_LIST_IS_FOR)
        + _render_tiles(runs)
        + f'<p class="skipped">The list skipped {skipped} run directories it could not read.</p>'
        + _render_chips(filters, "state", "every state", list(RUN_STATES))
        + _render_chips(filters, "wave", "every wave", _list_values(runs, "wave"))
        + _render_chips(filters, "task", "every task", _list_values(runs, "task"))
        + _render_sections(runs)
    )
