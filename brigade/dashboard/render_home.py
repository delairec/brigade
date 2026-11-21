from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from shlex import quote as quote_argument
from urllib.parse import quote

from brigade.dashboard.render_action import render_action
from brigade.dashboard.render_empty_state import render_empty_state
from brigade.dashboard.render_html_table import render_html_table
from brigade.dashboard.render_needs_you_row import NeedsYou, render_needs_you_row
from brigade.dashboard.render_page_head import PageHead, render_page_head
from brigade.dashboard.render_segment_strip import Segment, render_segment_strip
from brigade.dashboard.render_stat_tile import StatTile, render_stat_tile
from brigade.dashboard.render_status_pill import render_status_pill
from brigade.dashboard.render_verdict import Verdict, render_verdict
from brigade.inbox.render_age import render_age
from brigade.system.instant_formats import COMPACT_INSTANT_FORMAT

HOME_HEAD = PageHead("Home", "Whether brigade is working, what waits for you, and what it will do next.")
STOPPED = "brigade is stopped: the scheduler reports the tick stale."
WORKING = "brigade is working: a run is live."
IDLE_WITHOUT_WAVE = "brigade is idle: no wave is open."
IDLE_ON_HALTED_WAVES = "brigade is idle: every open wave is halted."
IDLE_UNTIL_THE_TICK = "brigade is idle: the open waves wait for the next tick."
FAILED = "failed"
RUNNING = "running"
PARKED = "parked"
BLOCKED = "blocked"
IDLE = "idle"
ACTIVE = "active"
PAUSED = "paused"
MERGED = "merged"
HALTED_MARK = "II"
QUESTION_MARK = "?"
STALE_MARK = "~"
NO_COMMAND = ""
INBOX_LINK = "#inbox"
NOTHING = "\u2013"
RUN_ID_SEPARATOR = "-"
LAST_RUN_FORMAT = "%m-%d %H:%MZ"
STUDY_RUN_COMMAND = "brigade study run <study>"


@dataclass(frozen=True)
class LastDayCount:
    kind: str
    one: str
    many: str
    view: str


LAST_DAY_LINES = (
    (
        LastDayCount("wave.started", "wave started", "waves started", "waves"),
        LastDayCount("wave.closed", "closed", "closed", "waves"),
    ),
    (
        LastDayCount("task.pr_opened", "pull request opened", "pull requests opened", "waves"),
        LastDayCount("pr.merged", "merged", "merged", "waves"),
    ),
    (LastDayCount("milestone.reported", "milestone reported", "milestones reported", "reports"),),
    (LastDayCount("run.finished", "run segment finished", "run segments finished", "runs"),),
    (LastDayCount("tick.action_failed", "failed tick action", "failed tick actions", "ledger"),),
)


@dataclass(frozen=True)
class HomeDocuments:
    status: dict
    scheduler: dict
    ledger: dict
    inbox: dict


def _describe_halt(halt: dict) -> str:
    if halt["resume_at"] is None:
        return f"parked on {halt['reason']}"
    return f"blocked on {halt['reason']} until {halt['resume_at']}"


def _read_wave_state(wave: dict) -> str:
    halt = wave["halt"]
    if halt is None:
        return RUNNING
    return PARKED if halt["resume_at"] is None else BLOCKED


def _render_section(heading: str, body: str) -> str:
    return f"<section><h2>{heading}</h2>{body}</section>"


def _halted_waves(status: dict) -> list[dict]:
    return [wave for wave in status["waves"] if wave["halt"] is not None]


def _judge_brigade(home: HomeDocuments) -> tuple[str, str]:
    status = home.status
    if home.scheduler["stale"]:
        return STOPPED, FAILED
    if status["live_runs"]:
        return WORKING, RUNNING
    idle_tone = PARKED if _list_needs_you(home) else IDLE
    if not status["waves"]:
        return IDLE_WITHOUT_WAVE, idle_tone
    if len(_halted_waves(status)) == len(status["waves"]):
        return IDLE_ON_HALTED_WAVES, idle_tone
    return IDLE_UNTIL_THE_TICK, idle_tone


def _explain_what_waits(needs_you: list[NeedsYou]) -> str:
    if not needs_you:
        return "Nothing waits for you."
    return f"Waiting for you: {len(needs_you)}, listed under Needs you."


def _list_scan_rows(scans: list[dict]) -> list[NeedsYou]:
    if not scans:
        return []
    studies = ", ".join(scan["study"] for scan in scans)
    signals = sum(scan["signals"] for scan in scans)
    oldest = max(scan["oldest_age_s"] for scan in scans)
    return [
        NeedsYou(
            f"{len(scans)} scans are parked: {studies}",
            f"{signals} new signals, the oldest {render_age(oldest)}",
            STUDY_RUN_COMMAND,
            oldest,
            HALTED_MARK,
            PARKED,
        )
    ]


def _list_inbox_rows(home: HomeDocuments) -> list[NeedsYou]:
    patterns = len(home.inbox["patterns"])
    proposed = [
        NeedsYou(
            f"{patterns} proposed patterns wait for a decision",
            "the inbox proposes them for ratification",
            NO_COMMAND,
            mark=QUESTION_MARK,
            state=PARKED,
            link=("Decide in the inbox", INBOX_LINK),
        )
    ]
    return [*(proposed if patterns else []), *_list_scan_rows(home.status["inbox"]["scans"])]


def _list_merges_and_orders(status: dict) -> list[NeedsYou]:
    merges = [
        NeedsYou(
            f"Milestone {merge['milestone']} of {merge['project']} waits for your merge",
            f"pull request {merge['pr']} is open",
            f"cd {quote_argument(merge['repository'])} && gh pr merge {merge['pr']}",
            merge["age_s"],
            QUESTION_MARK,
            PARKED,
        )
        for merge in status["awaiting_merge"]
    ]
    orders = [
        NeedsYou(
            f"Order {order['name']} of {order['project']} is parked",
            f"parked at {order['step']}: {order['reason']}",
            f"brigade order resume {order['name']}",
            order["age_s"],
            HALTED_MARK,
            PARKED,
        )
        for order in status["orders"]
    ]
    return [*merges, *orders]


def _list_needs_you(home: HomeDocuments) -> list[NeedsYou]:
    halted = [
        NeedsYou(
            f"Wave {wave['wave']} is halted",
            _describe_halt(wave["halt"]),
            f"brigade wave resume {wave['wave']}",
            wave["halt"]["age_s"],
            HALTED_MARK,
            _read_wave_state(wave),
        )
        for wave in _halted_waves(home.status)
    ]
    return [*halted, *_list_inbox_rows(home), *_list_merges_and_orders(home.status)]


def _list_stale_stalls(status: dict) -> list[NeedsYou]:
    merged = [stall for stall in status["inbox"]["stalls"] if stall["merged"]]
    if not merged:
        return []
    tasks = ", ".join(f"{stall['task']} of {stall['wave']}" for stall in merged)
    return [
        NeedsYou(
            f"{len(merged)} stall signals name tasks that merged since",
            tasks,
            NO_COMMAND,
            mark=STALE_MARK,
            link=("Review", INBOX_LINK),
        )
    ]


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
            f"{sum(quota['usage'].values()):,}",
            f"over {quota['window_hours']} hours, blocking {blocked}",
        ),
    ]
    return f'<div class="stat-tiles">{"".join(render_stat_tile(tile) for tile in tiles)}</div>'


def _render_needs_you(status: dict, needs_you: list[NeedsYou]) -> str:
    rows = [*needs_you, *_list_stale_stalls(status)]
    if not rows:
        return _render_section(
            "Needs you",
            render_empty_state(
                "nothing needs you",
                "a halted wave, a proposed pattern, a parked scan, a pull request to merge or a parked order"
                " would show here",
            ),
        )
    return _render_section(
        "Needs you", f'<ul class="needs-you-list">{"".join(render_needs_you_row(row) for row in rows)}</ul>'
    )


def _render_link(view: str, name: str) -> str:
    return f'<a href="#{view}/{escape(quote(name, safe=""))}">{escape(name)}</a>'


def _render_tasks(wave: dict) -> str:
    states = wave["task_states"]
    segments = [Segment(f"{state} {count}", state, count) for state, count in states.items()]
    strip = render_segment_strip(f"tasks of {wave['wave']}", segments)
    return f'{strip} <span class="muted num">{states.get(MERGED, 0)} of {wave["tasks"]} merged</span>'


def _render_live_runs(name: str, live_runs: list[dict]) -> str:
    runs = [
        f'{_render_link("runs", run["run"])}<br><span class="muted">{escape(run["slot"])} · {escape(str(run["task"]))}</span>'
        for run in live_runs
        if run["wave"] == name
    ]
    return "<br>".join(runs) or NOTHING


def _render_wave_row(wave: dict, live_runs: list[dict]) -> tuple[str, ...]:
    name = wave["wave"]
    return (
        f'{_render_link("waves", name)}<br><span class="muted">{escape(wave["project"])}</span>',
        render_status_pill(_read_wave_state(wave)),
        _render_tasks(wave),
        _render_live_runs(name, live_runs),
    )


def _render_at_work(status: dict) -> str:
    if not status["waves"]:
        return _render_section(
            "At work",
            render_empty_state("no wave is open", "the tick starts a wave once a milestone holds a ratified task"),
        )
    rows = [_render_wave_row(wave, status["live_runs"]) for wave in status["waves"]]
    return _render_section("At work", render_html_table(("wave", "state", "tasks", "live run"), rows, ""))


def _render_last_day_count(events: dict, count: LastDayCount) -> str:
    number = events.get(count.kind, 0)
    return f'<a href="#{count.view}">{number} {count.one if number == 1 else count.many}</a>'


def _render_last_day_line(events: dict, counts: tuple[LastDayCount, ...]) -> str:
    return f"<li>{', '.join(_render_last_day_count(events, count) for count in counts)}</li>"


def _render_last_day(events: dict) -> str:
    lines = "".join(_render_last_day_line(events, counts) for counts in LAST_DAY_LINES)
    return _render_section("Last 24 hours", f'<ul class="lines">{lines}</ul>')


def _render_forge(project: dict) -> str:
    if project["remote"] is None:
        return escape(project["forge"])
    return f'{escape(project["forge"])} · <span class="mono">{escape(project["remote"])}</span>'


def _render_corpus(project: dict) -> str:
    if not project["corpus"]:
        return NOTHING
    return f'<a href="#awawa/{escape(quote(project["name"], safe=""))}">corpus</a>'


def _render_project_row(project: dict, waves: list[dict]) -> tuple[str, ...]:
    name = project["name"]
    open_waves = sum(1 for wave in waves if wave["project"] == name)
    state, action = (PAUSED, "resume") if project["paused"] else (ACTIVE, "pause")
    return (
        escape(name),
        render_status_pill(state),
        _render_forge(project),
        str(open_waves),
        _render_corpus(project),
        render_action(("projects", name, action), action),
    )


def _render_projects(status: dict) -> str:
    rows = [_render_project_row(project, status["waves"]) for project in status["projects"]]
    table = render_html_table(
        ("project", "state", "forge", "open waves", "corpus", ""), rows, "no project is registered"
    )
    return _render_section("Projects", table)


def _format_last_run(run: str | None) -> str:
    if run is None:
        return NOTHING
    started = datetime.strptime(run.split(RUN_ID_SEPARATOR)[0], COMPACT_INSTANT_FORMAT).replace(tzinfo=UTC)
    return started.strftime(LAST_RUN_FORMAT)


def _render_study_row(study: dict, signals: dict[str, int]) -> tuple[str, ...]:
    name = study["name"]
    outcome = study["outcome"]
    now = (
        "due, runs at the next tick"
        if study["due"]
        else f'waits for <code class="cmd">brigade study run {escape(quote_argument(name))}</code>'
    )
    return (
        escape(name),
        escape(study["every"]),
        _format_last_run(study["last_run"]),
        NOTHING if outcome is None else render_status_pill(outcome),
        now,
        str(signals[name]) if name in signals else NOTHING,
    )


def _render_routine(status: dict) -> str:
    signals = {scan["study"]: scan["signals"] for scan in status["inbox"]["scans"]}
    rows = [_render_study_row(study, signals) for study in status["studies"]]
    header = ("study", "every", "last run", "outcome", "now", "new signals")
    table = render_html_table(header, rows, "no study is registered")
    return _render_section("Routine", table)


def render_home(home: HomeDocuments) -> str:
    status = home.status
    needs_you = _list_needs_you(home)
    sentence, state = _judge_brigade(home)
    return "".join(
        [
            render_page_head(HOME_HEAD),
            render_verdict(Verdict(sentence, _explain_what_waits(needs_you), state)),
            _render_tiles(home, needs_you),
            _render_needs_you(status, needs_you),
            _render_at_work(status),
            _render_last_day(home.ledger["events"]),
            _render_routine(status),
            _render_projects(status),
        ]
    )
