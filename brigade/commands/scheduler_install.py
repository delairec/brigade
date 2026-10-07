import sys
from pathlib import Path

from brigade.errors import ToolNotFound
from brigade.system.ask_scheduler import SchedulerQuestion, ask_scheduler
from brigade.system.locate_unit_directory import locate_unit_directory
from brigade.system.read_optional_configuration import read_optional_configuration
from brigade.system.read_user_systemd_state import SYSTEMD_STATES_FIT_FOR_TIMERS, read_user_systemd_state
from brigade.system.resolve_plugin import resolve_plugin

DOCUMENT_SCHEMA_VERSION = 1
CONFIGURATION_FILE = "config.toml"
LOG_FILE = "tick.log"


def _probe_scheduler(runtime) -> str:
    try:
        systemd_state = read_user_systemd_state(runtime.run_process)
    except ToolNotFound:
        return "cron"
    return "systemd" if systemd_state in SYSTEMD_STATES_FIT_FOR_TIMERS else "cron"


def _describe_install_request(runtime) -> dict:
    paths = runtime.paths
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "brigade": str(Path(sys.argv[0]).absolute()),
        "environment": {
            "PATH": paths.executable_search_path,
            "XDG_CONFIG_HOME": str(paths.config_root.parent),
            "XDG_STATE_HOME": str(paths.state_root.parent),
            "XDG_CACHE_HOME": str(paths.cache_root.parent),
        },
        "unit_directory": str(locate_unit_directory(paths)),
        "log_file": str(paths.state_root / LOG_FILE),
    }


def scheduler_install(request, runtime) -> dict:
    configuration = read_optional_configuration(runtime.paths.config_root / CONFIGURATION_FILE)
    if configuration.scheduler is not None:
        name, chosen_by = configuration.scheduler, "configuration"
    else:
        name, chosen_by = _probe_scheduler(runtime), "probe"
    answer = ask_scheduler(
        resolve_plugin("scheduler", name, runtime),
        SchedulerQuestion(scheduler_name=name, operation="install", request=_describe_install_request(runtime)),
        runtime,
    )
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "scheduler": answer["scheduler"],
        "chosen_by": chosen_by,
        "unit_files": answer["unit_files"],
        "cron_line": answer["cron_line"],
        "keep_running": answer["keep_running"],
    }
