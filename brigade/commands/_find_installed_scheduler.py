from brigade.runtime import Runtime
from brigade.system.ask_scheduler import SchedulerQuestion, ask_scheduler
from brigade.system.locate_unit_directory import locate_unit_directory
from brigade.system.scheduler_state import SchedulerState

DOCUMENT_SCHEMA_VERSION = 1
SCHEDULERS_ASKED = ("systemd", "cron")
NO_SCHEDULER = "none"
NOT_INSTALLED = SchedulerState(installed=False, unit_files=(), cron_line=None, next_activation=None)


def find_installed_scheduler(runtime: Runtime) -> tuple[str, SchedulerState]:
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
