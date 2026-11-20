from dataclasses import dataclass
from html import escape
from shlex import quote as quote_argument
from urllib.parse import quote

from brigade.dashboard.render_action import render_action
from brigade.dashboard.render_empty_state import render_empty_state
from brigade.dashboard.render_needs_you_row import NeedsYou, render_needs_you_row
from brigade.dashboard.render_stat_tile import StatTile, render_stat_tile
from brigade.dashboard.render_status_sentence import render_status_sentence
from brigade.inbox.render_age import render_age

DUE = "due"
FAILED_TICK_ACTION = "tick.action_failed"
INBOX_COMMAND = "brigade inbox list"
STOPPED = "brigade is stopped: the scheduler reports the tick stale."
WORKING = "brigade is working: a run is live."
IDLE_WITHOUT_WAVE = "brigade is idle: no wave is open."
IDLE_ON_HALTED_WAVES = "brigade is idle: every open wave is halted."
IDLE_UNTIL_THE_TICK = "brigade is idle: the open waves wait for the next tick."


@dataclass(frozen=True)
class HomeDocuments:
    status: dict
    scheduler: dict
    ledger: dict
    inbox: dict
    dry_run: dict


def _describe_halt(halt: dict) -> str:
    if halt["resume_at"] is None:
        return f"parked on {halt['reason']}"
    return f"blocked on {halt['reason']} until {halt['resume_at']}"


def _render_section(heading: str, body: str) -> str:
    return f"<section><h2>{heading}</h2>{body}</section>"


def _render_list(items: list[str]) -> str:
    return f"<ul>{''.join(f'<li>{item}</li>' for item in items)}</ul>"


def _render_rows(rows: list[NeedsYou]) -> str:
    return f'<ul class="needs-you-list">{"".join(render_needs_you_row(row) for row in rows)}</ul>'


def _halted_waves(status: dict) -> list[dict]:
    return [wave for wave in status["waves"] if wave["halt"] is not None]


def _say_what_brigade_does(home: HomeDocuments) -> str:
    status = home.status
    if home.scheduler["stale"]:
        return STOPPED
    if status["live_runs"]:
        return WORKING
    if not status["waves"]:
        return IDLE_WITHOUT_WAVE
    if len(_halted_waves(status)) == len(status["waves"]):
        return IDLE_ON_HALTED_WAVES
    return IDLE_UNTIL_THE_TICK


def _list_inbox_rows(home: HomeDocuments) -> list[NeedsYou]:
    patterns = len(home.inbox["patterns"])
    proposed = [NeedsYou(f"{patterns} proposed patterns", "the inbox proposes them for ratification", INBOX_COMMAND)]
    scans = [
        NeedsYou(
            scan["study"],
            f"{scan['signals']} new signals, the oldest {render_age(scan['oldest_age_s'])}",
            INBOX_COMMAND,
            scan["oldest_age_s"],
        )
        for scan in home.status["inbox"]["scans"]
    ]
    return [*(proposed if patterns else []), *scans]


def _list_merges_and_orders(status: dict) -> list[NeedsYou]:
    merges = [
        NeedsYou(
            f"{merge['milestone']} of {merge['project']}",
            f"pull request {merge['pr']} waits for your merge",
            f"cd {quote_argument(merge['repository'])} && gh pr merge {merge['pr']}",
            merge["age_s"],
        )
        for merge in status["awaiting_merge"]
    ]
    orders = [
        NeedsYou(
            f"{order['name']} of {order['project']}",
            f"parked at {order['step']}: {order['reason']}",
            f"brigade order resume {order['name']}",
            order["age_s"],
        )
        for order in status["orders"]
    ]
    return [*merges, *orders]


def _list_needs_you(home: HomeDocuments) -> list[NeedsYou]:
    halted = [
        NeedsYou(
            wave["wave"], _describe_halt(wave["halt"]), f"brigade wave resume {wave['wave']}", wave["halt"]["age_s"]
        )
        for wave in _halted_waves(home.status)
    ]
    return [*halted, *_list_inbox_rows(home), *_list_merges_and_orders(home.status)]


def _describe_oldest(needs_you: list[NeedsYou]) -> str:
    ages = [row.age_s for row in needs_you if row.age_s is not None]
    return f"the oldest {render_age(max(ages))}" if ages else "no age recorded"


def _render_tiles(home: HomeDocuments, needs_you: list[NeedsYou]) -> str:
    status = home.status
    quota = status["quota"]
    blocked = ", ".join(wave["wave"] for wave in quota["blocked_waves"]) or "no wave"
    tiles = [
        StatTile("open waves", str(len(status["waves"])), f"{len(_halted_waves(status))} halted"),
        StatTile("live runs", str(len(status["live_runs"])), "now"),
        StatTile("need you", str(len(needs_you)), _describe_oldest(needs_you)),
        StatTile(
            "quota tokens",
            str(sum(quota["usage"].values())),
            f"over {quota['window_hours']} hours, blocking {blocked}",
        ),
    ]
    return f'<div class="stat-tiles">{"".join(render_stat_tile(tile) for tile in tiles)}</div>'


def _render_stale_stalls(status: dict) -> str:
    stale = [
        NeedsYou(f"stall of {stall['task']} in {stall['wave']}", "its task merged since", INBOX_COMMAND)
        for stall in status["inbox"]["stalls"]
        if stall["merged"]
    ]
    return f"<h3>Stale</h3>{_render_rows(stale)}" if stale else ""


def _render_needs_you(status: dict, needs_you: list[NeedsYou]) -> str:
    listed = (
        _render_rows(needs_you)
        if needs_you
        else render_empty_state(
            "nothing needs you",
            "a halted wave, a proposed pattern, a parked scan, a pull request to merge or a parked order would show here",
        )
    )
    return _render_section("Needs you", f"{listed}{_render_stale_stalls(status)}")


def _render_wave_at_work(wave: dict, live_runs: list[dict]) -> str:
    name = wave["wave"]
    states = ", ".join(f"{escape(state)} {count}" for state, count in wave["task_states"].items())
    runs = [
        f"{escape(run['run'])}, {escape(run['slot'])} on {escape(str(run['task']))}"
        for run in live_runs
        if run["wave"] == name
    ]
    return (
        f'<a href="#waves/{escape(quote(name, safe=""))}">{escape(name)}</a>'
        f" of {escape(wave['project'])}: {states}{_render_list(runs) if runs else ''}"
    )


def _render_at_work(status: dict) -> str:
    if not status["waves"]:
        return _render_section(
            "At work",
            render_empty_state("no wave is open", "the tick starts a wave once a milestone holds a ratified task"),
        )
    return _render_section(
        "At work", _render_list([_render_wave_at_work(wave, status["live_runs"]) for wave in status["waves"]])
    )


def _render_task_waiting(held: dict) -> str:
    wave = held["wave"]
    return (
        f'<a href="#waves/{escape(quote(wave, safe=""))}">{escape(wave)}</a>'
        f" {escape(held['task'])}: {escape(held['cause'])}"
    )


def _render_tasks_waiting(dry_run: dict) -> str:
    held = dry_run["tasks_not_launched"]
    if not held:
        return _render_section(
            "Tasks waiting",
            render_empty_state(
                "no task waits",
                "a queued or parked task the next tick does not launch would show here with its cause",
            ),
        )
    return _render_section("Tasks waiting", _render_list([_render_task_waiting(task) for task in held]))


def _render_project(project: dict) -> str:
    name = project["name"]
    if project["paused"]:
        return f"{escape(name)}, paused{render_action(('projects', name, 'resume'), 'resume')}"
    return f"{escape(name)}, active{render_action(('projects', name, 'pause'), 'pause')}"


def _render_study(study: dict) -> str:
    return f"{escape(study['name'])}, {DUE if study['due'] else escape(str(study['outcome']))}"


def _render_order(order: dict) -> str:
    return (
        f"{escape(order['name'])} of {escape(str(order['project']))},"
        f" parked at {escape(order['step'])}: {escape(order['reason'])}"
    )


def render_home(home: HomeDocuments) -> str:
    status = home.status
    needs_you = _list_needs_you(home)
    failed = home.ledger["events"].get(FAILED_TICK_ACTION, 0)
    return "".join(
        [
            render_status_sentence(_say_what_brigade_does(home)),
            _render_tiles(home, needs_you),
            _render_needs_you(status, needs_you),
            _render_at_work(status),
            _render_tasks_waiting(home.dry_run),
            _render_section("Last 24 hours", f"<p>{failed} failed tick actions</p>"),
            _render_section("Projects", _render_list([_render_project(project) for project in status["projects"]])),
            _render_section("Studies", _render_list([_render_study(study) for study in status["studies"]])),
            _render_section("Orders", _render_list([_render_order(order) for order in status["orders"]])),
        ]
    )
