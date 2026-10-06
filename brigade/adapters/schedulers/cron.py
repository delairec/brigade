import shlex
from importlib.resources import files
from pathlib import Path
from string import Template

from brigade.errors import ToolFailure, ToolNotFound
from brigade.system.run_process import ProcessRequest

SHIPPED_DATA = files("brigade.adapters.schedulers") / "data"
MARKER = "# brigade scheduler install"
NO_CRONTAB = "no crontab"
CRONTAB_DIRECTORY = "/"
CRONTAB_TIMEOUT_S = 30.0
CRONTAB_LISTING_EXIT_CODES = (0, 1)
DOCUMENT_SCHEMA_VERSION = 1


def _quote(value: str) -> str:
    return shlex.quote(value).replace("%", "\\%")


def _describe_cron_line(request: dict) -> str:
    log_file = Path(request["log_file"])
    template = Template((SHIPPED_DATA / "crontab-line.tpl").read_text(encoding="utf-8").rstrip("\n"))
    return template.substitute(
        state_directory=_quote(str(log_file.parent)),
        environment=" ".join(f"{name}={_quote(value)}" for name, value in request["environment"].items()),
        brigade=_quote(request["brigade"]),
        log_file=_quote(str(log_file)),
        marker=MARKER,
    )


def _list_crontab(runtime) -> list[str]:
    record = runtime.run_process(
        ProcessRequest(
            argv=("crontab", "-l"),
            cwd=CRONTAB_DIRECTORY,
            timeout_s=CRONTAB_TIMEOUT_S,
            acceptable_exit_codes=CRONTAB_LISTING_EXIT_CODES,
        )
    )
    if record.exit_code == 0:
        return record.stdout.splitlines()
    if NO_CRONTAB in record.stderr:
        return []
    raise ToolFailure(f"crontab -l exited {record.exit_code}: {record.stderr.strip()}")


def install(request: dict, runtime) -> dict:
    cron_line = _describe_cron_line(request)
    lines = [line for line in _list_crontab(runtime) if not line.endswith(MARKER)]
    runtime.run_process(
        ProcessRequest(
            argv=("crontab", "-"),
            cwd=CRONTAB_DIRECTORY,
            timeout_s=CRONTAB_TIMEOUT_S,
            stdin="".join(f"{line}\n" for line in [*lines, cron_line]),
        )
    )
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "scheduler": "cron",
        "unit_files": [],
        "cron_line": cron_line,
        "keep_running": None,
    }


def _find_cron_line(runtime) -> str | None:
    try:
        lines = _list_crontab(runtime)
    except ToolNotFound:
        return None
    return next((line for line in lines if line.endswith(MARKER)), None)


def read_status(request: dict, runtime) -> dict:
    cron_line = _find_cron_line(runtime)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "installed": cron_line is not None,
        "unit_files": [],
        "cron_line": cron_line,
        "next_activation": None,
    }
