from brigade.command import Command
from brigade.runtime import Runtime
from brigade.system.ask_scheduler import SchedulerQuestion, ask_scheduler
from brigade.system.locate_unit_directory import locate_unit_directory
from brigade.system.scheduler_state import SchedulerState
from brigade.tick.heartbeat import Heartbeat
from brigade.tick.read_heartbeat import read_heartbeat

DOCUMENT_SCHEMA_VERSION = 1
SCHEDULERS_ASKED = ("systemd", "cron")
NO_SCHEDULER = "none"
HEARTBEAT_NAME = "tick.json"
NOT_INSTALLED = SchedulerState(installed=False, unit_files=(), cron_line=None, next_activation=None)


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


def _describe_heartbeat(heartbeat: Heartbeat) -> dict:
    return {"ts": heartbeat.ts, "duration_ms": heartbeat.duration_ms, "actions_applied": heartbeat.actions_applied}


def _describe_last_tick(runtime: Runtime):
    heartbeat = read_heartbeat(runtime.paths.state_root / HEARTBEAT_NAME)
    if heartbeat is None:
        return None
    return _describe_heartbeat(heartbeat)


def _render_last_tick(last_tick) -> str:
    if last_tick is None:
        return "never"
    return f"{last_tick['ts']}, {last_tick['actions_applied']} actions applied in {last_tick['duration_ms']} ms"


def _render_text(document: dict) -> str:
    lines = [f"scheduler  {document['scheduler']}", *(f"unit       {unit}" for unit in document["unit_files"])]
    if document["cron_line"] is not None:
        lines.append(f"cron line  {document['cron_line']}")
    if document["next_activation"] is not None:
        lines.append(f"next       {document['next_activation']}")
    lines.append(f"last tick  {_render_last_tick(document['last_tick'])}")
    return "\n".join(lines)


def _read_request(options):
    return options


def _decide_exit_code(document: dict) -> int:
    return 0


def scheduler_status(request, runtime: Runtime) -> dict:
    name, status = _find_installed(runtime)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "scheduler": name,
        "unit_files": list(status.unit_files),
        "cron_line": status.cron_line,
        "next_activation": status.next_activation,
        "last_tick": _describe_last_tick(runtime),
    }


COMMAND = Command(
    path=("scheduler", "status"),
    help="report the scheduler installed",
    group_help="install what fires the tick, and report it",
    run=scheduler_status,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
