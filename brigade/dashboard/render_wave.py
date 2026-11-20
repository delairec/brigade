from dataclasses import dataclass
from html import escape
from urllib.parse import quote

from brigade.dashboard.render_action import render_action
from brigade.dashboard.render_details import render_details
from brigade.dashboard.render_html_table import render_html_table
from brigade.dashboard.render_page_head import PageHead, render_page_head
from brigade.dashboard.render_stat_tile import StatTile, render_stat_tile
from brigade.dashboard.render_status_pill import render_status_pill
from brigade.dashboard.render_status_sentence import render_status_sentence
from brigade.dashboard.render_wave_timeline import render_wave_timeline
from brigade.runs.format_duration import format_duration

ABSENT = "-"
QUEUED_STATE = "queued"
PARKED_STATE = "parked"
MERGED_STATE = "merged"
FLAGGED_ROUNDS = 3
GITHUB_FORGE = "github"
RUN_FINISHED_EVENT = "run.finished"
ACTION_FAILED_EVENT = "tick.action_failed"
HALTING_EVENTS = ("wave.parked", "wave.blocked")
ENDING_EVENTS = {"wave.closed": "closed", "wave.cancelled": "was cancelled"}
TASK_HEADER = ("Task", "State", "Pull request", "Rounds", "Runs", "Share of cost")
NO_COST = 0
WAVE_LEDE = "The tasks of one wave, what they cost, and what halted the wave."
ENDED_STATES = {"wave.closed": "closed", "wave.cancelled": "cancelled"}
HALTED_STATES = {"wave.parked": "parked", "wave.blocked": "blocked"}
RUNNING_STATE = "running"


@dataclass(frozen=True)
class WavePage:
    shown: dict
    project: dict | None


def _list_events(ledger: dict, name: str) -> list[dict]:
    return [event for event in ledger["events"] if event["event"] == name]


def _list_runs(ledger: dict) -> list[dict]:
    return list({event["fields"]["run"]: event for event in _list_events(ledger, RUN_FINISHED_EVENT)}.values())


def _describe_cost(ledger: dict) -> StatTile:
    runs = _list_runs(ledger)
    unpriced = [run for run in runs if "cost_usd" not in run["fields"]]
    amount = f"{ledger['cost_usd'] or NO_COST:.2f} USD"
    if not unpriced:
        return StatTile(label="cost", value=amount, perimeter="every run records its cost")
    return StatTile(
        label="cost",
        value=f"at least {amount}",
        perimeter=f"a floor: {len(unpriced)} of {len(runs)} runs records no cost",
    )


def _describe_halts(ledger: dict) -> StatTile:
    halted = format_duration(ledger["halted_ms"])
    if not ledger["halts"]:
        return StatTile(label="time halted", value=halted, perimeter="never halted")
    reasons = dict.fromkeys(
        event["fields"]["reason"] for name in HALTING_EVENTS for event in _list_events(ledger, name)
    )
    return StatTile(
        label="time halted", value=halted, perimeter=f"halts: {len(ledger['halts'])}, for {', '.join(reasons)}"
    )


def _count_tasks(shown: dict) -> str:
    states = [task["state"] for task in shown["tasks"]]
    return f"{states.count(MERGED_STATE)} of {len(states)} tasks merged, {states.count(PARKED_STATE)} parked"


def _render_tiles(shown: dict) -> str:
    ledger = shown["ledger"]
    run_time = sum(task["duration_ms"] or 0 for task in ledger["by_task"])
    turns = sum(ledger["turns_by_task"].values())
    states = [task["state"] for task in shown["tasks"]]
    tiles = [
        StatTile(
            label="tasks merged",
            value=f"{states.count(MERGED_STATE)} of {len(states)}",
            perimeter=f"{states.count(PARKED_STATE)} parked",
        ),
        StatTile(
            label="wall time",
            value=format_duration(ledger["wall_time_ms"]),
            perimeter=f"from {ledger['first']} to {ledger['last']}",
        ),
        StatTile(
            label="run time",
            value=format_duration(run_time),
            perimeter=f"{turns} turns over {len(_list_runs(ledger))} runs",
        ),
        _describe_cost(ledger),
        _describe_halts(ledger),
    ]
    return f'<div class="stat-tiles">{"".join(render_stat_tile(tile) for tile in tiles)}</div>'


def _is_halted(ledger: dict) -> bool:
    halts = ledger["halts"]
    return bool(halts) and halts[-1]["resumed_at"] is None


def _describe_standing(shown: dict) -> str:
    ledger = shown["ledger"]
    heading = f"Wave {shown['wave']} of {shown['project']}"
    ending = next((event for event in ledger["events"] if event["event"] in ENDING_EVENTS), None)
    if ending is not None:
        cost = _describe_cost(ledger).value
        return (
            f"{heading} {ENDING_EVENTS[ending['event']]} at {ending['at']}: {_count_tasks(shown)},"
            f" in {format_duration(ledger['wall_time_ms'])} for {cost}."
        )
    if _is_halted(ledger):
        return f"{heading} is halted since {ledger['halts'][-1]['halted_at']}: {_count_tasks(shown)}."
    return f"{heading} is running: {_count_tasks(shown)}."


def _read_state(ledger: dict) -> str:
    ending = next((event for event in ledger["events"] if event["event"] in ENDED_STATES), None)
    if ending is not None:
        return ENDED_STATES[ending["event"]]
    if _is_halted(ledger):
        halts = [event["event"] for event in ledger["events"] if event["event"] in HALTED_STATES]
        return HALTED_STATES[halts[-1]]
    return RUNNING_STATE


def _render_resume(shown: dict) -> str:
    if _is_halted(shown["ledger"]):
        return render_action(("waves", shown["wave"], "resume"), "resume")
    return ""


def _render_milestone(shown: dict) -> str:
    milestone = shown["milestone"]
    if milestone is None:
        return "<p>No milestone.</p>"
    report = shown["milestone_report"]
    if report is None:
        return f"<p>Milestone {escape(milestone)}.</p>"
    return f'<p>Milestone {escape(milestone)}, <a href="#reports/{escape(quote(report, safe=""))}">its report</a>.</p>'


def _read_pull_request_address(project: dict | None) -> str | None:
    if project is None:
        return None
    fields = {field["name"]: field["value"] for field in project["project"]["fields"]}
    if fields.get("FORGE") != GITHUB_FORGE or "REMOTE" not in fields:
        return None
    return f"https://github.com/{fields['REMOTE']}/pull/"


def _render_pull_request(number: int | None, address: str | None) -> str:
    if number is None:
        return ABSENT
    if address is None:
        return f"#{number}"
    return f'<a href="{escape(address)}{number}">#{number}</a>'


def _render_rounds(rounds: int) -> str:
    if rounds >= FLAGGED_ROUNDS:
        return f'<strong class="flagged">{rounds}</strong>'
    return str(rounds)


def _render_runs(task: dict, ledger: dict) -> str:
    finished = [run["fields"]["run"] for run in _list_runs(ledger) if run["fields"].get("task") == task["task"]]
    runs = [run for run in dict.fromkeys([*finished, task["run"]]) if run is not None]
    links = ", ".join(f'<a href="#runs/{escape(quote(run, safe=""))}">{escape(run)}</a>' for run in runs)
    return links or ABSENT


def _render_share(task: str, ledger: dict) -> str:
    cost = next((entry["cost_usd"] for entry in ledger["by_task"] if entry["task"] == task), None)
    total = ledger["cost_usd"]
    if cost is None or not total:
        return ABSENT
    return f"{cost / total:.0%}"


def _render_state(task: dict, wave: str) -> str:
    state = task["state"] or QUEUED_STATE
    if state == PARKED_STATE:
        return render_status_pill(state) + render_action(("waves", wave, "tasks", task["task"], "requeue"), "requeue")
    return render_status_pill(state)


def _render_tasks(page: WavePage) -> str:
    shown = page.shown
    ledger = shown["ledger"]
    address = _read_pull_request_address(page.project)
    rows = [
        (
            escape(task["task"]),
            _render_state(task, shown["wave"]),
            _render_pull_request(task["pull_request"], address),
            _render_rounds(ledger["rounds_by_task"].get(task["task"], 0)),
            _render_runs(task, ledger),
            _render_share(task["task"], ledger),
        )
        for task in shown["tasks"]
    ]
    return render_html_table(TASK_HEADER, rows, "The wave holds no task.")


def _describe_failure(action: str, failures: list[dict], ledger: dict) -> str:
    last = failures[-1]
    task = last["fields"].get("task")
    later = ledger["events"][ledger["events"].index(last) + 1 :]
    clearing = next(
        (event for event in later if event["event"] != ACTION_FAILED_EVENT and event["fields"].get("task") == task),
        None,
    )
    cleared = "not cleared in the ledger" if clearing is None else f"cleared by {clearing['event']} at {clearing['at']}"
    return (
        f"<li>{escape(action)}, failures: {len(failures)}, the last at {escape(last['at'])}:"
        f" {escape(last['fields']['error'])}; {escape(cleared)}</li>"
    )


def _render_failures(ledger: dict) -> str:
    by_action = {}
    for event in _list_events(ledger, ACTION_FAILED_EVENT):
        by_action.setdefault(event["fields"]["action"], []).append(event)
    if not by_action:
        return "<p>No tick action of the wave failed.</p>"
    items = "".join(_describe_failure(action, failures, ledger) for action, failures in by_action.items())
    return f'<ul class="failed-actions">{items}</ul>'


def _render_event(event: dict) -> str:
    task = event["fields"].get("task")
    subject = "" if task is None else f" {escape(task)}"
    return f"<li>{escape(event['at'])} {escape(event['event'])}{subject}</li>"


def render_wave(page: WavePage) -> str:
    shown = page.shown
    ledger = shown["ledger"]
    events = "".join(_render_event(event) for event in ledger["events"])
    head = PageHead(title="Wave", lede=WAVE_LEDE, name=shown["wave"], state=_read_state(ledger))
    return (
        f"{render_page_head(head)}<section><h2>Wave {escape(shown['wave'])} of {escape(shown['project'])}</h2>{_render_milestone(shown)}"
        f"{render_status_sentence(_describe_standing(shown))}{_render_resume(shown)}{_render_tiles(shown)}</section>"
        f"<section><h2>Tasks</h2>{_render_tasks(page)}</section>"
        f"<section><h2>How it went</h2>{render_wave_timeline(ledger)}{_render_failures(ledger)}</section>"
        f"{render_details('Events', f'<ol>{events}</ol>')}"
    )
