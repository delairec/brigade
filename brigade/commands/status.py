import argparse
from collections import Counter

from brigade.command import Command
from brigade.corpus.read_entities import Entity, read_entities
from brigade.inbox.read_inbox import NEW_STATUS, Signal, read_inbox
from brigade.inbox.render_age import render_age
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.milestone_closed import MilestoneClosed
from brigade.ledger.milestone_pr_opened import MilestonePrOpened
from brigade.ledger.order_parked import OrderParked
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.sum_quota_usage import sum_quota_usage
from brigade.orders.convert_order import convert_order
from brigade.orders.read_order_facts import ORDER_EVENTS
from brigade.registry.read_projects import read_projects
from brigade.registry.require_operational_corpus import require_operational_corpus
from brigade.runs.list_runs import list_runs
from brigade.runtime import Runtime
from brigade.studies.describe_study_row import describe_study_row
from brigade.studies.read_last_study_orders import read_last_study_orders
from brigade.studies.read_quota_resumes import read_quota_resumes
from brigade.studies.read_studies import read_studies
from brigade.studies.record_scan_signals import SCAN_KIND
from brigade.system.read_configuration import CONFIGURATION_OPTIONAL, read_configuration
from brigade.tick.build_snapshot import ORDER_ENTITY_TYPE
from brigade.tick.describe_heartbeat import describe_heartbeat
from brigade.tick.describe_study_facts import describe_study_facts
from brigade.tick.is_study_due import is_study_due
from brigade.tick.read_heartbeat import read_heartbeat
from brigade.tick.record_stall import SIGNAL_KIND as STALL_KIND
from brigade.waves.read_task_states import read_task_states
from brigade.waves.read_wave_pause import read_wave_pause
from brigade.waves.summarize_waves import summarize_waves

DOCUMENT_SCHEMA_VERSION = 1
PAUSED_STATUS = "paused"
ACTIVE_STATUS = "active"
QUOTA_REASON = "quota"
DUE = "due"
NEVER = "never"
FINGERPRINT_SEPARATOR = ":"
QUEUED_STATE = "queued"
MERGED_STATE = "merged"
LIVE_RUN_STATE = "running"


def _is_paused(project: Entity) -> bool:
    return any(field.name == "STATUS" and field.value == PAUSED_STATUS for field in project.fields)


def _list_open_waves(entries: tuple[LedgerEntry, ...]) -> list[dict]:
    events = tuple(entry.event for entry in entries)
    waves = []
    for summary in summarize_waves(entries):
        if not summary.is_open:
            continue
        pause = read_wave_pause(events, summary.started.wave)
        states = read_task_states(entries, summary.started.wave)
        waves.append(
            {
                "wave": summary.started.wave,
                "project": summary.started.project,
                "branch": summary.started.branch,
                "last_event": summary.last_event,
                "tasks": len(summary.started.tasks),
                "task_states": dict(Counter(states.get(task, QUEUED_STATE) for task in summary.started.tasks)),
                "halt": None if pause is None else pause.to_document(),
            }
        )
    return waves


def _describe_quota(entries: tuple[LedgerEntry, ...], waves: list[dict], runtime: Runtime) -> dict:
    window_hours = read_configuration(runtime, CONFIGURATION_OPTIONAL).quota_window_hours
    return {
        **sum_quota_usage(entries, runtime.now, window_hours),
        "blocked_waves": [
            {"wave": wave["wave"], "project": wave["project"], "resume_at": wave["halt"]["resume_at"]}
            for wave in waves
            if wave["halt"] is not None and wave["halt"]["reason"] == QUOTA_REASON
        ],
    }


def _list_studies_to_watch(runtime: Runtime) -> list[dict]:
    entries = read_ledger(runtime.paths.state_root).entries
    last_orders = read_last_study_orders(entries)
    quota_resumes = read_quota_resumes(runtime.paths.state_root, entries)
    studies = []
    for study in read_studies(runtime):
        last_order = last_orders.get(study.name)
        facts = describe_study_facts(study, last_order, quota_resumes)
        due = is_study_due(facts, runtime.now)
        if due or facts.parked:
            studies.append({**describe_study_row(study, last_order), "project": study.project, "due": due})
    return studies


def _list_parked_orders(runtime: Runtime, entries: tuple[LedgerEntry, ...]) -> list[dict]:
    last_events = {
        (entry.event.kind, entry.event.order): entry.event for entry in entries if isinstance(entry.event, ORDER_EVENTS)
    }
    orders = (
        convert_order(entity)
        for entity in read_entities(runtime.run_process, runtime.paths.config_root, ORDER_ENTITY_TYPE)
    )
    return [
        {
            "name": order.name,
            "recipe": order.recipe,
            "project": order.project,
            "run": parked.run,
            "step": parked.step,
            "reason": parked.reason,
        }
        for order in orders
        if isinstance(parked := last_events.get((order.recipe, order.name)), OrderParked)
    ]


def _list_scans(new_signals: list[Signal]) -> list[dict]:
    ages_by_scan: dict[tuple[str, str | None], list[int]] = {}
    for signal in new_signals:
        if signal.kind == SCAN_KIND:
            study = signal.fingerprint.partition(FINGERPRINT_SEPARATOR)[0]
            ages_by_scan.setdefault((study, signal.project), []).append(signal.age_s)
    return [
        {"study": study, "project": project, "signals": len(ages), "oldest_age_s": max(ages)}
        for (study, project), ages in sorted(ages_by_scan.items(), key=lambda item: item[0][0])
    ]


def _list_live_runs(runtime: Runtime) -> list[dict]:
    return [
        {"run": run["run"], "slot": run["slot"], "project": run["project"], "wave": run["wave"], "task": run["task"]}
        for run in list_runs(runtime.paths.state_root)["runs"]
        if run["state"] == LIVE_RUN_STATE
    ]


def _list_awaiting_merge(entries: tuple[LedgerEntry, ...]) -> list[dict]:
    opened = {}
    for entry in entries:
        if isinstance(entry.event, MilestonePrOpened):
            opened[(entry.event.project, entry.event.milestone)] = entry.event.pr
        if isinstance(entry.event, MilestoneClosed):
            opened.pop((entry.event.project, entry.event.milestone), None)
    return [{"project": project, "milestone": milestone, "pr": pr} for (project, milestone), pr in opened.items()]


def _list_stalls(new_signals: list[Signal], entries: tuple[LedgerEntry, ...]) -> list[dict]:
    stalls = []
    for signal in new_signals:
        if signal.kind == STALL_KIND:
            wave, task = signal.fingerprint.split(FINGERPRINT_SEPARATOR)[-2:]
            merged = read_task_states(entries, wave).get(task) == MERGED_STATE
            stalls.append({"project": signal.project, "wave": wave, "task": task, "merged": merged})
    return stalls


def _describe_halt(pause: dict) -> str:
    if pause["resume_at"] is None:
        return f"parked on {pause['reason']}"
    return f"blocked on {pause['reason']} until {pause['resume_at']}"


def _render_wave(wave: dict) -> str:
    line = f"wave       {wave['wave']} of {wave['project']}, {wave['last_event']}"
    return line if wave["halt"] is None else f"{line}, {_describe_halt(wave['halt'])}"


def _render_quota(quota: dict) -> str:
    usage = ", ".join(f"{measure} {tokens}" for measure, tokens in quota["usage"].items())
    return f"quota      over {quota['window_hours']} hours: {usage}; {quota['runs_without_usage']} runs without usage"


def _render_last_tick(last_tick: dict | None) -> str:
    if last_tick is None:
        return NEVER
    return f"{last_tick['ts']}, {last_tick['actions_applied']} actions applied in {last_tick['duration_ms']} ms"


def _render_scan(scan: dict) -> str:
    return f"scan       {scan['study']}, {scan['signals']} new signals, the oldest {render_age(scan['oldest_age_s'])}"


def _render_study(study: dict) -> str:
    return f"study      {study['name']}, {DUE if study['due'] else study['outcome']}"


def _render_order(order: dict) -> str:
    return f"order      {order['name']} of {order['project']}, parked at {order['step']}: {order['reason']}"


def _render_text(document: dict) -> str:
    return "\n".join(
        [
            *(
                f"project    {project['name']}, {PAUSED_STATUS if project['paused'] else ACTIVE_STATUS}"
                for project in document["projects"]
            ),
            *(_render_wave(wave) for wave in document["waves"]),
            f"inbox      {document['inbox']['new_signals']} new signals",
            *(_render_scan(scan) for scan in document["inbox"]["scans"]),
            _render_quota(document["quota"]),
            f"last tick  {_render_last_tick(document['last_tick'])}",
            *(_render_study(study) for study in document["studies"]),
            *(_render_order(order) for order in document["orders"]),
        ]
    )


def status(request: argparse.Namespace, runtime: Runtime) -> dict:
    require_operational_corpus(runtime.paths)
    entries = read_ledger(runtime.paths.state_root).entries
    waves = _list_open_waves(entries)
    new_signals = [
        signal for signal in read_inbox(runtime.paths.state_root, runtime.now) if signal.status == NEW_STATUS
    ]
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "projects": [{"name": project.name, "paused": _is_paused(project)} for project in read_projects(runtime)],
        "waves": waves,
        "live_runs": _list_live_runs(runtime),
        "awaiting_merge": _list_awaiting_merge(entries),
        "inbox": {
            "new_signals": len(new_signals),
            "scans": _list_scans(new_signals),
            "stalls": _list_stalls(new_signals, entries),
        },
        "quota": _describe_quota(entries, waves, runtime),
        "last_tick": describe_heartbeat(read_heartbeat(runtime.paths.heartbeat_file)),
        "studies": _list_studies_to_watch(runtime),
        "orders": _list_parked_orders(runtime, entries),
    }


COMMAND = Command(
    path=("status",),
    help="print the Home document: the projects, the open waves, the inbox and the scans holding new signals, the quota, the last tick and the studies",
    run=status,
    render_text=_render_text,
)
