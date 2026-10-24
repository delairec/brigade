import argparse
import sys
from pathlib import Path

from brigade.command import Command
from brigade.runtime import Runtime
from brigade.system.ask_scheduler import SchedulerQuestion, ask_scheduler
from brigade.system.choose_scheduler import choose_scheduler
from brigade.system.describe_linger_warning import describe_linger_warning
from brigade.system.locate_unit_directory import locate_unit_directory
from brigade.system.read_configuration import CONFIGURATION_OPTIONAL, read_configuration

DOCUMENT_SCHEMA_VERSION = 1
LOG_FILE = "tick.log"
CHOOSERS = {"configuration": "config.toml", "probe": "the probe of the user systemd instance"}


def _describe_install_request(runtime: Runtime) -> dict:
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


def _render_text(document: dict) -> str:
    name = document["scheduler"]
    chooser = CHOOSERS[document["chosen_by"]]
    if document["keep_running"] is not None:
        lines = [f"{name} chosen by {chooser}: nothing installed; keep this command running", document["keep_running"]]
    else:
        lines = [f"{name} installed, chosen by {chooser}", *(f"unit  {unit}" for unit in document["unit_files"])]
        if document["cron_line"] is not None:
            lines.append(f"cron line  {document['cron_line']}")
    lines.extend(f"warning  {warning}" for warning in document["warnings"])
    return "\n".join(lines)


def _list_warnings(scheduler: str, runtime: Runtime) -> list[str]:
    if scheduler != "systemd":
        return []
    warning = describe_linger_warning(runtime.run_process)
    return [] if warning is None else [warning]


def scheduler_install(request: argparse.Namespace, runtime: Runtime) -> dict:
    configuration = read_configuration(runtime, CONFIGURATION_OPTIONAL)
    choice = choose_scheduler(configuration.scheduler, runtime.run_process)
    answer = ask_scheduler(
        runtime.resolve_plugin("scheduler", choice.name),
        SchedulerQuestion(scheduler_name=choice.name, operation="install", request=_describe_install_request(runtime)),
        runtime,
    )
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "scheduler": answer.scheduler,
        "chosen_by": choice.chosen_by,
        "unit_files": list(answer.unit_files),
        "cron_line": answer.cron_line,
        "keep_running": answer.keep_running,
        "warnings": _list_warnings(answer.scheduler, runtime),
    }


COMMAND = Command(
    path=("scheduler", "install"),
    help="install the scheduler config.toml names, or the default",
    group_help="install what fires the tick, and report it",
    run=scheduler_install,
    render_text=_render_text,
)
