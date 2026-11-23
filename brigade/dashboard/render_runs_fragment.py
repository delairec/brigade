from collections import Counter
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from html import escape
from urllib.parse import quote, urlencode

from brigade.dashboard.render_block import Block, render_block
from brigade.dashboard.render_callout import render_callout
from brigade.dashboard.render_empty_state import render_empty_state
from brigade.dashboard.render_field import render_field
from brigade.dashboard.render_filter_chips import FilterChip, render_filter_chips
from brigade.dashboard.render_html_table import render_html_table
from brigade.dashboard.render_page_head import PageHead, render_page_head
from brigade.dashboard.render_segment_squares import render_segment_squares
from brigade.dashboard.render_stat_tile import StatTile, render_stat_tile
from brigade.dashboard.render_status_pill import render_status_pill
from brigade.dashboard.render_status_sentence import render_status_sentence
from brigade.runs.format_duration import format_duration
from brigade.runs.format_run_arguments import format_run_arguments
from brigade.runs.list_segment_outcomes import list_segment_outcomes

RUNS_VIEW = "runs"
HEADER = (
    ("", "Started"),
    ("", "Run"),
    ("", "Procedure"),
    ("", "Role"),
    ("", "Task"),
    ("", "Outcome"),
    ("", "Segments"),
    ("num", "Duration"),
    ("num", "Cost"),
    ("", "Arguments"),
)
COST_HEADER = ("procedure", "runs", "cost")
FLOOR = "at least "
NO_DURATION = 0
NO_COST = 0
ABSENT = "-"
RUN_STATES = ("running", "finished", "dead")
LIVE = "running"
FINISHED = "finished"
DEAD = "dead"
LIMIT_OUTCOMES = ("soft_limit", "turn_limit", "wall_limit")
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


@dataclass(frozen=True)
class RunsPage:
    listing: dict
    every_run: dict
    filters: RunFilters


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
    offered = sorted({*values, chosen} - {None})
    options += "".join(
        _render_option(value, value, _address(replace(filters, **{name: value})), chosen=value == chosen)
        for value in offered
    )
    selector = f"{RUNS_VIEW}-{name}"
    return render_field(name.capitalize(), selector, f'<select id="{selector}" name="{name}">{options}</select>')


def _render_selects(filters: RunFilters, runs: list[dict]) -> str:
    return (
        f'<div class="filters">{_render_select(filters, "wave", _list_values(runs, "wave"))}'
        f"{_render_select(filters, 'task', _list_values(runs, 'task'))}</div>"
    )


def _list_values(runs: list[dict], field: str) -> set[str]:
    return {run[field] for run in runs if run[field] is not None}


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


def _show_measure(shown: str | None, *, partial: bool) -> str:
    if shown is None:
        return ABSENT
    return f"{FLOOR}{shown}" if partial else shown


def _show_duration(run: dict) -> str:
    duration_ms = run["duration_ms"]
    shown = None if duration_ms is None else format_duration(duration_ms)
    return _show_measure(shown, partial=run["duration_partial"])


def _show_cost(run: dict) -> str:
    cost_usd = run["cost_usd"]
    shown = None if cost_usd is None else f"${cost_usd:.2f}"
    return _show_measure(shown, partial=run["cost_partial"])


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
        f"<td>{render_segment_squares(list_segment_outcomes(run['state'], run['segments']))}</td>",
        f'<td class="num">{_show_duration(run)}</td>',
        f'<td class="num">{_show_cost(run)}</td>',
        f'<td class="mono">{escape(format_run_arguments(run["arguments"]))}</td>',
    )
    return f"<tr>{''.join(cells)}</tr>"


def _render_table(runs: list[dict]) -> str:
    if not runs:
        return render_empty_state(NO_RUN_MATCHES, WHAT_WOULD_FILL)
    newest_first = sorted(runs, key=lambda run: run["started_at"], reverse=True)
    header = "".join(f'<th class="{kind}">{name}</th>' if kind else f"<th>{name}</th>" for kind, name in HEADER)
    rows = "".join(_render_row(run) for run in newest_first)
    return f'<div class="panel scroll"><table><thead><tr>{header}</tr></thead><tbody>{rows}</tbody></table></div>'


def _records_no_cost(run: dict) -> bool:
    return run["cost_usd"] is None or run["cost_partial"]


def _show_total_cost(runs: list[dict]) -> str:
    total = sum(run["cost_usd"] or NO_COST for run in runs)
    floor = FLOOR if any(_records_no_cost(run) for run in runs) else ""
    return f"{floor}${total:.2f}"


def _describe_total_cost(runs: list[dict]) -> StatTile:
    uncosted = sum(_records_no_cost(run) for run in runs)
    perimeter = f"over the runs listed; runs lacking a cost: {uncosted}"
    return StatTile(label="cost", value=_show_total_cost(runs), perimeter=perimeter)


def _render_procedure_cost(procedure: str, runs: list[dict]) -> tuple[str, ...]:
    of_procedure = [run for run in runs if run["procedure"] == procedure]
    return escape(procedure), str(len(of_procedure)), _show_total_cost(of_procedure)


def _render_cost_by_procedure(runs: list[dict]) -> str:
    if not runs:
        return ""
    rows = [_render_procedure_cost(procedure, runs) for procedure in sorted({run["procedure"] for run in runs})]
    table = render_html_table(COST_HEADER, rows, NO_RUN_MATCHES)
    return render_block(
        Block(title="Where the cost went", lede=f"The {len(runs)} runs listed, by procedure.", body=table)
    )


def _render_tiles(runs: list[dict]) -> str:
    states = Counter(run["state"] for run in runs)
    outcomes = Counter(run["outcome"] for run in runs if run["state"] == FINISHED)
    finished = " · ".join(f"{count} {outcome.replace('_', ' ')}" for outcome, count in sorted(outcomes.items()))
    tiles = [
        StatTile(label="live", value=str(states[LIVE]), perimeter=f"of {len(runs)} runs listed"),
        StatTile(label=FINISHED, value=str(states[FINISHED]), perimeter=finished),
        StatTile(label=DEAD, value=str(states[DEAD]), perimeter="runs whose process ended without a result"),
        StatTile(
            label="run time",
            value=format_duration(sum(run["duration_ms"] or NO_DURATION for run in runs)),
            perimeter="over the segments that ended",
        ),
        _describe_total_cost(runs),
    ]
    return f'<div class="stat-tiles">{"".join(render_stat_tile(tile) for tile in tiles)}</div>'


def _name_latest(runs: list[dict]) -> str:
    latest = max(runs, key=lambda run: run["started_at"])
    task = "" if latest["task"] is None else f" on {latest['task']}"
    return f"the latest {latest['run']}{task}"


def _describe_limit_cut(procedure: str, outcome: str, runs: list[dict]) -> str:
    counted = f"1 {procedure} run was" if len(runs) == 1 else f"{len(runs)} {procedure} runs were"
    return f"{counted} cut at the {outcome.replace('_', ' ')}, {_name_latest(runs)}."


def _render_gone_wrong(runs: list[dict]) -> str:
    cut: dict[tuple[str, str], list[dict]] = {}
    for run in runs:
        if run["state"] == FINISHED and run["outcome"] in LIMIT_OUTCOMES:
            cut.setdefault((run["procedure"], run["outcome"]), []).append(run)
    most_first = sorted(cut.items(), key=lambda group: len(group[1]), reverse=True)
    callouts = [
        render_callout(outcome, _describe_limit_cut(procedure, outcome, cut_runs))
        for (procedure, outcome), cut_runs in most_first
    ]
    dead = [run for run in runs if run["state"] == DEAD]
    if dead:
        counted = "1 run is" if len(dead) == 1 else f"{len(dead)} runs are"
        callouts.append(
            render_callout(DEAD, f"{counted} dead, its process gone without a result: {_name_latest(dead)}.")
        )
    return "".join(callouts)


def _describe_listing(runs: list[dict]) -> str:
    states = Counter(run["state"] for run in runs)
    return f"{len(runs)} runs listed: {states[LIVE]} live, {states[FINISHED]} finished, {states[DEAD]} dead."


def render_runs_fragment(page: RunsPage) -> str:
    filters = page.filters
    runs = page.listing["runs"]
    skipped = len(page.listing["skipped"])
    return (
        render_page_head(HEAD)
        + render_status_sentence(_describe_listing(runs))
        + _render_explainer(WHAT_A_RUN_IS)
        + _render_chips(filters, runs)
        + _render_selects(filters, page.every_run["runs"])
        + _render_tiles(runs)
        + _render_cost_by_procedure(runs)
        + _render_gone_wrong(runs)
        + f'<p class="skipped">The list skipped {skipped} run directories it could not read.</p>'
        + _render_table(runs)
    )
