from collections import Counter
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from html import escape
from urllib.parse import quote, urlencode

from brigade.dashboard.render_empty_state import render_empty_state
from brigade.dashboard.render_field import render_field
from brigade.dashboard.render_filter_chips import FilterChip, render_filter_chips
from brigade.dashboard.render_page_head import PageHead, render_page_head
from brigade.dashboard.render_stat_tile import StatTile, render_stat_tile
from brigade.dashboard.render_status_pill import render_status_pill
from brigade.dashboard.render_status_sentence import render_status_sentence

RUNS_VIEW = "runs"
HEADER = ("Started", "Run", "Procedure", "Role", "Task", "Outcome")
ABSENT = "-"
RUN_STATES = ("running", "finished", "dead")
LIVE = "running"
FINISHED = "finished"
DEAD = "dead"
EVERY_STATE = "All"
SHORT_ID_MARK = "…"
STAMP_SEPARATOR = "T"
WHAT_A_RUN_IS = (
    (
        "A run is one procedure a role carries out through a client, for a task of a wave or on its own. It runs in"
        " segments: a segment is one session of the client, and a segment that reaches the cap of its role hands over"
        " to the next through the progress of the run."
    ),
    (
        "A run is running while its process lives, finished once it has a result, dead when the process is gone"
        " without one. Come here to follow a live run, or to find which run of a task went wrong."
    ),
)
NO_RUN_MATCHES = "No run matches these filters."
WHAT_WOULD_FILL = "A run appears here once the tick or brigade run starts a procedure."
HEAD = PageHead(
    title="Runs",
    lede="A run is one agent at work: a procedure, such as a build or a review, played by a role on a task.",
)


@dataclass(frozen=True)
class RunFilters:
    state: str | None
    wave: str | None
    task: str | None


def _address(filters: RunFilters) -> str:
    chosen = {name: value for name, value in vars(filters).items() if value is not None}
    return f"{RUNS_VIEW}?{urlencode(chosen)}" if chosen else RUNS_VIEW


def _render_explainer(paragraphs: tuple[str, ...]) -> str:
    body = "".join(f"<p>{escape(paragraph)}</p>" for paragraph in paragraphs)
    return f'<details class="explainer"><summary>How to read this page</summary><div>{body}</div></details>'


def _render_chips(filters: RunFilters, runs: list[dict]) -> str:
    states = Counter(run["state"] for run in runs)
    chips = [
        FilterChip(
            label=EVERY_STATE,
            view=_address(replace(filters, state=None)),
            chosen=filters.state is None,
            count=len(runs),
        )
    ]
    chips += [
        FilterChip(
            label=state.capitalize(),
            view=_address(replace(filters, state=state)),
            chosen=filters.state == state,
            count=states[state],
        )
        for state in RUN_STATES
    ]
    return render_filter_chips(chips)


def _render_option(value: str, label: str, address: str, *, chosen: bool) -> str:
    selected = " selected" if chosen else ""
    return f'<option value="{escape(value)}" data-href="{escape(address)}"{selected}>{escape(label)}</option>'


def _render_select(filters: RunFilters, name: str, values: list[str]) -> str:
    chosen = getattr(filters, name)
    options = _render_option("", "any", _address(replace(filters, **{name: None})), chosen=chosen is None)
    options += "".join(
        _render_option(value, value, _address(replace(filters, **{name: value})), chosen=value == chosen)
        for value in values
    )
    selector = f"{RUNS_VIEW}-{name}"
    return render_field(name.capitalize(), selector, f'<select id="{selector}" name="{name}">{options}</select>')


def _render_selects(filters: RunFilters, runs: list[dict]) -> str:
    return (
        f'<div class="filters">{_render_select(filters, "wave", _list_values(runs, "wave"))}'
        f"{_render_select(filters, 'task', _list_values(runs, 'task'))}</div>"
    )


def _list_values(runs: list[dict], field: str) -> list[str]:
    return sorted({run[field] for run in runs if run[field] is not None})


def _render_link(address: str, label: str, title: str) -> str:
    named = f' title="{escape(title)}"' if title else ""
    return f'<a class="mono" href="#{escape(address)}"{named}>{escape(label)}</a>'


def _render_task(run: dict) -> str:
    if run["task"] is None:
        return ABSENT
    if run["wave"] is None:
        return f'<span class="mono">{escape(run["task"])}</span>'
    return _render_link(f"waves/{quote(run['wave'], safe='')}", run["task"], "")


def _show_state(run: dict) -> str:
    return run["outcome"] if run["state"] == FINISHED else run["state"]


def _show_start(started_at: str) -> str:
    return datetime.fromisoformat(started_at).astimezone(UTC).strftime("%m-%d %H:%MZ")


def _shorten(run: str) -> str:
    return SHORT_ID_MARK + run.partition(STAMP_SEPARATOR)[2]


def _render_run_link(run: str) -> str:
    return _render_link(f"{RUNS_VIEW}/{quote(run, safe='')}", _shorten(run), run)


def _render_row(run: dict) -> str:
    cells = (
        f'<td class="num">{escape(_show_start(run["started_at"]))}</td>',
        f"<td>{_render_run_link(run['run'])}</td>",
        f"<td>{escape(run['procedure'])}</td>",
        f"<td>{escape(run['role'])}</td>",
        f"<td>{_render_task(run)}</td>",
        f"<td>{render_status_pill(_show_state(run))}</td>",
    )
    return f"<tr>{''.join(cells)}</tr>"


def _render_table(runs: list[dict]) -> str:
    if not runs:
        return render_empty_state(NO_RUN_MATCHES, WHAT_WOULD_FILL)
    newest_first = sorted(runs, key=lambda run: run["started_at"], reverse=True)
    header = "".join(f"<th>{name}</th>" for name in HEADER)
    rows = "".join(_render_row(run) for run in newest_first)
    return f'<div class="panel scroll"><table><thead><tr>{header}</tr></thead><tbody>{rows}</tbody></table></div>'


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
        render_page_head(HEAD)
        + render_status_sentence(_describe_listing(runs))
        + _render_explainer(WHAT_A_RUN_IS)
        + _render_tiles(runs)
        + f'<p class="skipped">The list skipped {skipped} run directories it could not read.</p>'
        + _render_chips(filters, runs)
        + _render_selects(filters, runs)
        + _render_table(runs)
    )
