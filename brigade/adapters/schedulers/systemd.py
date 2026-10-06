from importlib.resources import files
from pathlib import Path
from string import Template

from brigade.errors import ToolNotFound
from brigade.system.create_directory import create_directory
from brigade.system.run_process import EVERY_EXIT_CODE, ProcessRequest
from brigade.system.write_text_file import write_text_file

SHIPPED_DATA = files("brigade.adapters.schedulers") / "data"
SERVICE_NAME = "brigade.service"
TIMER_NAME = "brigade.timer"
SYSTEMCTL_DIRECTORY = "/"
SYSTEMCTL_TIMEOUT_S = 30.0
NO_NEXT_ACTIVATION = "n/a"
DOCUMENT_SCHEMA_VERSION = 1
UNIT_ESCAPES = (("\\", "\\\\"), ('"', '\\"'), ("%", "%%"))
COMMAND_ESCAPES = (*UNIT_ESCAPES, ("$", "$$"))


def _escape(value: str, escapes: tuple) -> str:
    for character, replacement in escapes:
        value = value.replace(character, replacement)
    return value


def _render(template_name: str, **values: str) -> str:
    return Template((SHIPPED_DATA / template_name).read_text(encoding="utf-8")).substitute(values)


def _run_systemctl(runtime, *arguments: str, acceptable_exit_codes: tuple = (0,)):
    return runtime.run_process(
        ProcessRequest(
            argv=("systemctl", "--user", *arguments),
            cwd=SYSTEMCTL_DIRECTORY,
            timeout_s=SYSTEMCTL_TIMEOUT_S,
            acceptable_exit_codes=acceptable_exit_codes,
        )
    )


def _locate_units(request: dict) -> tuple[Path, Path]:
    unit_directory = Path(request["unit_directory"])
    return unit_directory / SERVICE_NAME, unit_directory / TIMER_NAME


def install(request: dict, runtime) -> dict:
    service, timer = _locate_units(request)
    environment = "\n".join(
        f'Environment="{_escape(f"{name}={value}", UNIT_ESCAPES)}"' for name, value in request["environment"].items()
    )
    create_directory(service.parent)
    write_text_file(
        service,
        _render("brigade.service.tpl", environment=environment, brigade=_escape(request["brigade"], COMMAND_ESCAPES)),
    )
    write_text_file(timer, _render("brigade.timer.tpl"))
    _run_systemctl(runtime, "daemon-reload")
    _run_systemctl(runtime, "enable", "--now", TIMER_NAME)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "scheduler": "systemd",
        "unit_files": [str(service), str(timer)],
        "cron_line": None,
        "keep_running": None,
    }


def _read_next_activation(runtime):
    try:
        record = _run_systemctl(
            runtime,
            "show",
            TIMER_NAME,
            "--property=NextElapseUSecRealtime",
            "--value",
            acceptable_exit_codes=EVERY_EXIT_CODE,
        )
    except ToolNotFound:
        return None
    value = record.stdout.strip()
    if record.exit_code != 0 or not value or value == NO_NEXT_ACTIVATION:
        return None
    return value


def read_status(request: dict, runtime) -> dict:
    unit_files = [str(unit) for unit in _locate_units(request) if unit.exists()]
    installed = bool(unit_files)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "installed": installed,
        "unit_files": unit_files,
        "cron_line": None,
        "next_activation": _read_next_activation(runtime) if installed else None,
    }
