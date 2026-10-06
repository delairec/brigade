from brigade.system.ask_scheduler import SchedulerQuestion, ask_scheduler
from brigade.system.locate_unit_directory import locate_unit_directory
from brigade.tick.read_heartbeat import read_heartbeat

DOCUMENT_SCHEMA_VERSION = 1
SCHEDULERS_ASKED = ("systemd", "cron")
NO_SCHEDULER = "none"
HEARTBEAT_NAME = "tick.json"


def _find_installed(runtime):
    request = {"schema_version": DOCUMENT_SCHEMA_VERSION, "unit_directory": str(locate_unit_directory(runtime.paths))}
    for name in SCHEDULERS_ASKED:
        status = ask_scheduler(
            SchedulerQuestion(scheduler_name=name, operation="read_status", request=request), runtime
        )
        if status["installed"]:
            return name, status
    return NO_SCHEDULER, {"unit_files": [], "cron_line": None, "next_activation": None}


def _describe_last_tick(runtime):
    heartbeat = read_heartbeat(runtime.paths.state_root / HEARTBEAT_NAME)
    if heartbeat is None:
        return None
    return {key: value for key, value in heartbeat.items() if key != "schema_version"}


def scheduler_status(request, runtime) -> dict:
    name, status = _find_installed(runtime)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "scheduler": name,
        "unit_files": status["unit_files"],
        "cron_line": status["cron_line"],
        "next_activation": status["next_activation"],
        "last_tick": _describe_last_tick(runtime),
    }
