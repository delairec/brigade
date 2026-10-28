import argparse
from datetime import datetime, timedelta

from brigade.command import Command
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.read_ledger import read_ledger
from brigade.runtime import Runtime
from brigade.system.ask_scheduler import SchedulerQuestion, ask_scheduler
from brigade.system.locate_unit_directory import locate_unit_directory
from brigade.system.read_configuration import CONFIGURATION_OPTIONAL, read_configuration
from brigade.system.scheduler_state import SchedulerState
from brigade.tick.describe_heartbeat import describe_heartbeat
from brigade.tick.heartbeat import Heartbeat
from brigade.tick.read_heartbeat import read_heartbeat
from brigade.waves.read_task_state import PARKED_STATE, TASK_EVENTS, read_task_state
from brigade.waves.read_wave_pause import read_wave_pause
from brigade.waves.summarize_waves import summarize_waves

DOCUMENT_SCHEMA_VERSION = 1
SCHEDULERS_ASKED = ("systemd", "cron")
NO_SCHEDULER = "none"
NOT_INSTALLED = SchedulerState(installed=False, unit_files=(), cron_line=None, next_activation=None)
STALE_EXIT_CODE = 1


def _find_installed(runtime: Runtime):
    request = {"schema_version": DOCUMENT_SCHEMA_VERSION, "unit_directory": str(locate_unit_directory(runtime.paths))}
    for name in SCHEDULERS_ASKED:
        status = ask_scheduler(
            runtime.resolve_plugin("scheduler", name),
            SchedulerQuestion(scheduler_name=name, operation="read_status", request=request),
            runtime,
        )
        if status.installed:
            return name, status
    return NO_SCHEDULER, NOT_INSTALLED


def _is_stale(heartbeat: Heartbeat | None, status: SchedulerState, now: datetime, minutes: int) -> bool:
    if heartbeat is None:
        return status.installed
    return now - datetime.fromisoformat(heartbeat.ts) > timedelta(minutes=minutes)


def _list_open_waves(entries: tuple[LedgerEntry, ...]) -> list[str]:
    return [summary.started.wave for summary in summarize_waves(entries) if summary.is_open]


def _list_paused_waves(events: tuple, waves: list[str]) -> list[dict]:
    pauses = [(wave, read_wave_pause(events, wave)) for wave in waves]
    return [{"wave": wave, **pause.to_document()} for wave, pause in pauses if pause is not None]


def _list_parked_tasks(events: tuple, waves: list[str]) -> list[dict]:
    last_events = {
        (event.wave, event.task): event for event in events if isinstance(event, TASK_EVENTS) and event.wave in waves
    }
    return [
        {"task": task, "wave": wave, "reason": event.reason}
        for (wave, task), event in last_events.items()
        if read_task_state(event) == PARKED_STATE
    ]


def _render_last_tick(last_tick) -> str:
    if last_tick is None:
        return "never"
    return f"{last_tick['ts']}, {last_tick['actions_applied']} actions applied in {last_tick['duration_ms']} ms"


def _render_staleness(document: dict) -> str:
    if document["last_tick"] is None:
        return "no tick ran while a scheduler is installed"
    return f"the last tick is older than {document['tick_stale_after']} minutes"


def _render_resumption(pause: dict) -> str:
    if pause["resume_at"] is None:
        return "resumes on brigade wave resume"
    return f"resumes at {pause['resume_at']}"


def _render_parked_task(task: dict) -> str:
    if task["reason"] is None:
        return f"parked     {task['task']} of {task['wave']}"
    return f"parked     {task['task']} of {task['wave']}, {task['reason']}"


def _render_text(document: dict) -> str:
    lines = [f"scheduler  {document['scheduler']}", *(f"unit       {unit}" for unit in document["unit_files"])]
    if document["cron_line"] is not None:
        lines.append(f"cron line  {document['cron_line']}")
    if document["next_activation"] is not None:
        lines.append(f"next       {document['next_activation']}")
    lines.append(f"last tick  {_render_last_tick(document['last_tick'])}")
    if document["stale"]:
        lines.append(f"stale      {_render_staleness(document)}")
    lines.extend(
        f"paused     {pause['wave']}, {pause['reason']}, {_render_resumption(pause)}"
        for pause in document["paused_waves"]
    )
    lines.extend(_render_parked_task(task) for task in document["parked_tasks"])
    return "\n".join(lines)


def _decide_exit_code(document: dict) -> int:
    return STALE_EXIT_CODE if document["stale"] else 0


def scheduler_status(request: argparse.Namespace, runtime: Runtime) -> dict:
    name, status = _find_installed(runtime)
    minutes = read_configuration(runtime, CONFIGURATION_OPTIONAL).tick_stale_after
    heartbeat = read_heartbeat(runtime.paths.heartbeat_file)
    entries = read_ledger(runtime.paths.state_root).entries
    events = tuple(entry.event for entry in entries)
    open_waves = _list_open_waves(entries)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "scheduler": name,
        "unit_files": list(status.unit_files),
        "cron_line": status.cron_line,
        "next_activation": status.next_activation,
        "last_tick": describe_heartbeat(heartbeat),
        "tick_stale_after": minutes,
        "stale": _is_stale(heartbeat, status, runtime.now, minutes),
        "paused_waves": _list_paused_waves(events, open_waves),
        "parked_tasks": _list_parked_tasks(events, open_waves),
    }


COMMAND = Command(
    path=("scheduler", "status"),
    help="report the scheduler installed, whether its tick is stale, the paused waves and the parked tasks",
    group_help="install what fires the tick, and report it",
    run=scheduler_status,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
