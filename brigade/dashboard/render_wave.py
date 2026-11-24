import re
from collections import Counter
from dataclasses import dataclass
from html import escape
from urllib.parse import quote

from brigade.dashboard.awawa_address import AwawaAddress
from brigade.dashboard.format_clock import format_clock
from brigade.dashboard.format_span import format_span
from brigade.dashboard.render_action import render_action
from brigade.dashboard.render_block import Block, render_block
from brigade.dashboard.render_callout import render_callout
from brigade.dashboard.render_fold import Fold, render_fold
from brigade.dashboard.render_page_head import Crumb, PageHead, render_page_head
from brigade.dashboard.render_stat_tile import StatTile, render_stat_tile
from brigade.dashboard.render_status_pill import render_status_pill
from brigade.dashboard.render_wave_timeline import render_wave_timeline
from brigade.ledger.count_runs import RunCount, count_runs
from brigade.waves.describe_halt_document import describe_halt_document

ABSENT = "-"
QUEUED_STATE = "queued"
PARKED_STATE = "parked"
HALT_STATE = "blocked"
NO_PREDECESSOR = "nothing"
MERGED_STATE = "merged"
RUNNING_STATE = "running"
FLAGGED_ROUNDS = 3
NO_ROUNDS = 0
NO_TURNS = 0
NO_COST = 0
NO_RUNS_KEPT = frozenset()
GITHUB_FORGE = "github"
ENTITY_PARAMETER = "entity"
TASK_REFERENCE_PREFIX = "@TASK."
RUN_FINISHED_EVENT = "run.finished"
ACTION_FAILED_EVENT = "tick.action_failed"
ENDED_STATES = {"wave.closed": "closed", "wave.cancelled": "cancelled"}
HALTED_STATES = {"wave.parked": "parked", "wave.blocked": "blocked"}
HALT_NOUNS = {"wave.parked": "park", "wave.blocked": "block"}
HALT_HEADER = ("Halt", "Reason", "From", "Until", "Lasted", "Way out")
TASK_HEADER = (
    "Task",
    "State",
    "Pull request",
    "Rounds",
    "Turns",
    "Run time",
    "Cost, share of the wave",
    "Last run",
)
EVENT_HEADER = ("At", "Event", "Task", "What")
SUMMED_KINDS = 4
DATED_RUN = re.compile(r"\d{8}T(\d{6}Z-.+)")
FORGE_MESSAGE = re.compile(r"GraphQL: (.+?)(?: \(\w+\))?$")
TASK_SEPARATOR = ", "


@dataclass(frozen=True)
class WavePage:
    shown: dict
    project: dict | None
    runs: dict | None = None


def _count(amount: int, noun: str) -> str:
    if amount == 1:
        return f"{amount} {noun}"
    return f"{amount} {noun}s"


def _render_cell(cell: tuple[str, str]) -> str:
    classes, content = cell
    if not classes:
        return f"<td>{content}</td>"
    return f'<td class="{classes}">{content}</td>'


def _render_table(header: tuple[str, ...], rows: list[tuple[tuple[str, str], ...]]) -> str:
    head = "".join(f"<th>{escape(name)}</th>" for name in header)
    body = "".join(f"<tr>{''.join(_render_cell(cell) for cell in row)}</tr>" for row in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _list_events(ledger: dict, name: str) -> list[dict]:
    return [event for event in ledger["events"] if event["event"] == name]


def _count_runs(ledger: dict) -> RunCount:
    return count_runs(event["fields"] for event in _list_events(ledger, RUN_FINISHED_EVENT))


def _pair_halts(ledger: dict) -> list[tuple[dict, dict]]:
    halting = [event for event in ledger["events"] if event["event"] in HALTED_STATES]
    return list(zip(ledger["halts"], halting, strict=False))


def _is_halted(ledger: dict) -> bool:
    halts = ledger["halts"]
    return bool(halts) and halts[-1]["resumed_at"] is None


def _find_ending(ledger: dict) -> dict | None:
    return next((event for event in ledger["events"] if event["event"] in ENDED_STATES), None)


def _find_entry(task: str, ledger: dict) -> dict | None:
    return next((entry for entry in ledger["by_task"] if entry["task"] == task), None)


def _read_rounds(task: str, ledger: dict) -> int:
    merged = {entry["task"]: entry["rounds"] for entry in ledger.get("pull_requests", [])}
    return merged.get(task, ledger["rounds_by_task"].get(task, NO_ROUNDS))


def _read_share(cost: float, total: float) -> int:
    return round(cost / total * 100)


def _describe_cost(ledger: dict) -> StatTile:
    count = _count_runs(ledger)
    amount = f"{ledger['cost_usd'] or NO_COST:.2f} USD"
    if not count.costless:
        return StatTile(label="cost", value=amount, perimeter="every run records its cost")
    verb = "records" if count.costless == 1 else "record"
    return StatTile(
        label="cost",
        value=f"at least {amount}",
        perimeter=f"a floor: {count.costless} of {count.runs} runs {verb} no cost",
    )


def _describe_halts(ledger: dict) -> StatTile:
    halted = format_span(ledger["halted_ms"])
    if not ledger["halts"]:
        return StatTile(label="time halted", value=halted, perimeter="never halted")
    kinds = [event["event"] for event in ledger["events"] if event["event"] in HALT_NOUNS]
    counts = [_count(kinds.count(name), noun) for name, noun in HALT_NOUNS.items() if name in kinds]
    reasons = dict.fromkeys(event["fields"]["reason"] for event in ledger["events"] if event["event"] in HALT_NOUNS)
    return StatTile(label="time halted", value=halted, perimeter=", ".join([*counts, *reasons]))


def _render_tiles(shown: dict) -> str:
    ledger = shown["ledger"]
    run_time = sum(entry["duration_ms"] or 0 for entry in ledger["by_task"])
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
            value=format_span(ledger["wall_time_ms"]),
            perimeter=f"{format_clock(ledger['first'])} → {format_clock(ledger['last'])}",
        ),
        StatTile(
            label="run time",
            value=format_span(run_time),
            perimeter=f"{turns} turns · {_count_runs(ledger).runs} runs",
        ),
        _describe_cost(ledger),
        _describe_halts(ledger),
    ]
    return f'<div class="stat-tiles">{"".join(render_stat_tile(tile) for tile in tiles)}</div>'


def _count_tasks(shown: dict) -> str:
    states = [task["state"] for task in shown["tasks"]]
    merged = states.count(MERGED_STATE)
    if merged == len(states) == 1:
        return "Its one task merged"
    if merged == len(states):
        return f"All {len(states)} tasks merged"
    return f"{merged} of {len(states)} tasks merged, {states.count(PARKED_STATE)} parked"


def _describe_standing(shown: dict) -> str:
    ledger = shown["ledger"]
    counted = _count_tasks(shown)
    if _find_ending(ledger) is not None:
        return f"{counted} in {format_span(ledger['wall_time_ms'])}, for {_describe_cost(ledger).value}."
    if _is_halted(ledger):
        halt, event = _pair_halts(ledger)[-1]
        return f"{counted}, halted since {format_clock(halt['halted_at'])} for {event['fields']['reason']}."
    return f"{counted}, running for {format_span(ledger['wall_time_ms'])}."


def _describe_costliest(ledger: dict) -> str:
    total = ledger["cost_usd"]
    if not total:
        return ""
    entry = max(ledger["by_task"], key=lambda entry: entry["cost_usd"] or NO_COST)
    return (
        f" {entry['task']} took {_read_share(entry['cost_usd'], total)} % of the cost"
        f" and {_read_rounds(entry['task'], ledger)} review rounds."
    )


def _read_state(ledger: dict) -> str:
    ending = _find_ending(ledger)
    if ending is not None:
        return ENDED_STATES[ending["event"]]
    if _is_halted(ledger):
        return HALTED_STATES[_pair_halts(ledger)[-1][1]["event"]]
    return RUNNING_STATE


def _list_crumbs(shown: dict) -> tuple[Crumb, ...]:
    crumbs = (Crumb(label="Waves", address="#waves"), Crumb(label=shown["project"], address=""))
    milestone = shown["milestone"]
    if milestone is None:
        return crumbs
    report = shown["milestone_report"]
    address = "" if report is None else f"#reports/{quote(report, safe='')}"
    return (*crumbs, Crumb(label=milestone, address=address))


def _render_head(shown: dict) -> str:
    ledger = shown["ledger"]
    head = PageHead(
        title="Wave",
        lede=_describe_standing(shown) + _describe_costliest(ledger),
        name=shown["wave"],
        state=_read_state(ledger),
        crumbs=_list_crumbs(shown),
    )
    return render_page_head(head)


def _render_way_out(state: str, wave: str) -> str:
    if state == PARKED_STATE:
        action = f"/api/waves/{quote(wave, safe='')}/resume"
        return f'<button class="btn btn-primary" type="button" data-post="{escape(action)}">Resume</button>'
    return "resumes by itself"


def _render_halt(halt: dict, event: dict, wave: str) -> tuple[tuple[str, str], ...]:
    state = HALTED_STATES[event["event"]]
    if halt["resumed_at"] is None:
        until, lasted, way_out = ABSENT, ABSENT, _render_way_out(state, wave)
    else:
        until, lasted, way_out = format_clock(halt["resumed_at"]), format_span(halt["duration_ms"]), "resumed"
    return (
        ("", render_status_pill(state)),
        ("mono", escape(event["fields"]["reason"])),
        ("num", format_clock(halt["halted_at"])),
        ("num", until),
        ("num", lasted),
        ("", way_out),
    )


def _render_halts(shown: dict) -> str:
    ledger = shown["ledger"]
    if not ledger["halts"]:
        body = "<p>The wave never halted.</p>"
    else:
        rows = [_render_halt(halt, event, shown["wave"]) for halt, event in _pair_halts(ledger)]
        body = f'<div class="panel scroll">{_render_table(HALT_HEADER, rows)}</div>'
    current = (
        ""
        if shown["halt"] is None
        else render_callout(HALT_STATE, describe_halt_document(shown["wave"], shown["halt"]))
    )
    return render_block(
        Block(
            title="Why it waited",
            lede="The halts of the wave, and the way out of the current one.",
            body=current + body,
        )
    )


def _render_plan(task: dict) -> str:
    if "after" not in task:
        return ""
    after = ", ".join(task["after"]) or NO_PREDECESSOR
    specs = "".join(f"<li>{escape(spec)}</li>" for spec in task["spec"])
    return render_fold(Fold(summary="Plan", detail=f"after {after}", body=f'<ul class="steps">{specs}</ul>'))


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


def _render_state(task: dict, wave: str) -> str:
    state = task["state"] or QUEUED_STATE
    if state == PARKED_STATE:
        return render_status_pill(state) + render_action(("waves", wave, "tasks", task["task"], "requeue"), "requeue")
    if task["reason"] is not None:
        return f'{render_status_pill(state)} <span class="cause">{escape(task["reason"])}</span>'
    return render_status_pill(state)


def _render_rounds(task: str, ledger: dict) -> tuple[str, str]:
    rounds = _read_rounds(task, ledger)
    if rounds >= FLAGGED_ROUNDS:
        return ("num flag", str(rounds))
    return ("num", str(rounds))


def _render_run_time(entry: dict | None) -> str:
    duration = None if entry is None else entry["duration_ms"]
    if duration is None:
        return ABSENT
    return format_span(duration)


def _render_cost(entry: dict | None, total: float | None) -> str:
    cost = None if entry is None else entry["cost_usd"]
    if cost is None or not total:
        return ABSENT
    share = _read_share(cost, total)
    return (
        f'<svg class="bar" viewBox="0 0 100 8" preserveAspectRatio="none" role="img" aria-label="{share} percent of'
        f' the cost"><rect class="g-track" width="100" height="8"></rect><rect class="g-ink" width="{share}"'
        f' height="8"></rect></svg>{cost:.2f} USD · {share} %'
    )


def _render_last_run(run: str | None, kept: frozenset) -> str:
    if run is None:
        return ABSENT
    dated = DATED_RUN.fullmatch(run)
    label = run if dated is None else f"…{dated.group(1)}"
    if run not in kept:
        return f'<span class="mono">{escape(label)}</span>'
    title = "" if dated is None else f' title="{escape(run)}"'
    return f'<a class="mono" href="#runs/{escape(quote(run, safe=""))}"{title}>{escape(label)}</a>'


def _render_task_link(task: str, project: str) -> str:
    address = AwawaAddress(project).setting(ENTITY_PARAMETER, f"{TASK_REFERENCE_PREFIX}{task}").link()
    return f'<a class="mono" href="{escape(address)}">{escape(task)}</a>'


def _render_task(task: dict, page: WavePage, kept: frozenset) -> tuple[tuple[str, str], ...]:
    ledger = page.shown["ledger"]
    entry = _find_entry(task["task"], ledger)
    return (
        ("", _render_task_link(task["task"], page.shown["project"]) + _render_plan(task)),
        ("", _render_state(task, page.shown["wave"])),
        ("", _render_pull_request(task["pull_request"], _read_pull_request_address(page.project))),
        _render_rounds(task["task"], ledger),
        ("num", str(ledger["turns_by_task"].get(task["task"], NO_TURNS))),
        ("num", _render_run_time(entry)),
        ("num", _render_cost(entry, ledger["cost_usd"])),
        ("", _render_last_run(task["run"], kept)),
    )


def _render_tasks(page: WavePage) -> str:
    kept = NO_RUNS_KEPT if page.runs is None else frozenset(entry["run"] for entry in page.runs["runs"])
    rows = [_render_task(task, page, kept) for task in page.shown["tasks"]]
    body = f'<div class="panel scroll">{_render_table(TASK_HEADER, rows)}</div>'
    return render_block(Block(title="Tasks", lede="Each task with what it cost and where it stands.", body=body))


def _render_line(tag: str, text: str) -> str:
    return f'<li><p><span class="tag">{tag}</span>{escape(text)}</p></li>'


def _render_handovers(ledger: dict) -> list[str]:
    counts = Counter(handover["task"] for handover in ledger.get("handovers", []))
    return [
        _render_line(
            "Read", f"{task} was handed over {_count(amount, 'time')}, its run going on in a fresh segment each time."
        )
        for task, amount in counts.items()
    ]


def _read_error(error: str) -> str:
    message = FORGE_MESSAGE.search(error)
    return error if message is None else message.group(1)


def _describe_failure(action: str, failures: list[dict], ledger: dict) -> str:
    last = failures[-1]
    task = last["fields"].get("task")
    later = ledger["events"][ledger["events"].index(last) + 1 :]
    clearing = next(
        (event for event in later if event["event"] != ACTION_FAILED_EVENT and event["fields"].get("task") == task),
        None,
    )
    cleared = (
        "not cleared in the ledger"
        if clearing is None
        else f"cleared by {clearing['event']} at {format_clock(clearing['at'])}"
    )
    return (
        f"{action} failed {_count(len(failures), 'time')}, the last at {format_clock(last['at'])}:"
        f" {_read_error(last['fields']['error'])}; {cleared}."
    )


def _render_failures(ledger: dict) -> list[str]:
    by_action = {}
    for event in _list_events(ledger, ACTION_FAILED_EVENT):
        by_action.setdefault(event["fields"]["action"], []).append(event)
    if not by_action:
        return [_render_line("Read", "No tick action of the wave failed.")]
    return [
        _render_line("Failed", _describe_failure(action, failures, ledger)) for action, failures in by_action.items()
    ]


def _render_course(ledger: dict) -> str:
    lines = "".join([*_render_handovers(ledger), *_render_failures(ledger)])
    body = f'{render_wave_timeline(ledger)}<ul class="panel lines">{lines}</ul>'
    return render_block(Block(title="How it went", lede="Each task from its first run to its merge.", body=body))


def _describe_event(fields: dict) -> str:
    if "state" in fields:
        return render_status_pill(fields["state"])
    if "run" in fields:
        return escape(fields["run"])
    if "error" in fields:
        return escape(f"{fields['action']}: {fields['error']}")
    if "tasks" in fields:
        return escape(TASK_SEPARATOR.join(fields["tasks"]))
    return escape(fields.get("reason", ABSENT))


def _render_event(event: dict) -> tuple[tuple[str, str], ...]:
    task = event["fields"].get("task")
    return (
        ("num", format_clock(event["at"])),
        ("mono", escape(event["event"])),
        ("", ABSENT) if task is None else ("mono", escape(task)),
        ("", _describe_event(event["fields"])),
    )


def _summarize_kinds(events: list[dict]) -> str:
    counts = Counter(event["event"] for event in events).most_common()
    parts = [f"{amount} {kind}" for kind, amount in counts[:SUMMED_KINDS]]
    others = sum(amount for _, amount in counts[SUMMED_KINDS:])
    if others:
        parts.append(f"{others} others")
    return " · ".join(parts)


def _render_events(ledger: dict) -> str:
    events = ledger["events"]
    table = _render_table(EVENT_HEADER, [_render_event(event) for event in events])
    fold = Fold(summary="Show the events", detail=_summarize_kinds(events), body=f'<div class="scroll">{table}</div>')
    return render_block(
        Block(
            title="Events",
            lede=f"The {len(events)} events the ledger holds for the wave, in the order recorded.",
            body=f'<div class="panel">{render_fold(fold)}</div>',
        )
    )


def render_wave(page: WavePage) -> str:
    shown = page.shown
    ledger = shown["ledger"]
    return (
        f"{_render_head(shown)}{_render_tiles(shown)}{_render_halts(shown)}{_render_tasks(page)}"
        f"{_render_course(ledger)}{_render_events(ledger)}"
    )
