import sys

from brigade.corpus.read_awawa_version import read_awawa_version
from brigade.errors import ToolNotFound
from brigade.git.read_git_version import read_git_version
from brigade.python_floor import PYTHON_FLOOR
from brigade.system.resolve_plugin import resolve_plugin
from brigade.system.run_process import EVERY_EXIT_CODE, ProcessRequest

DOCUMENT_SCHEMA_VERSION = 1
AWAWA_FLOOR = (2, 7)
PROBE_DIRECTORY = "/"
PROBE_TIMEOUT_S = 10.0
SYSTEMD_STATES_FIT_FOR_TIMERS = ("running", "degraded")
SCHEDULER_FALLBACK = "a cron line, or brigade tick --loop"
FORGE_FALLBACK = "local mode without a forge"
AWAWA_WEB_FALLBACK = "the dashboard's corpus view only"


def _format_version(version: tuple[int, ...]) -> str:
    return ".".join(str(part) for part in version)


def _create_prerequisite(name: str, state: str, detail: str) -> dict:
    return {"name": name, "kind": "prerequisite", "state": state, "detail": detail, "fallback": None}


def _create_optional(name: str, state: str, detail: str, fallback: str) -> dict:
    return {"name": name, "kind": "optional", "state": state, "detail": detail, "fallback": fallback}


def _check_python() -> dict:
    running = _format_version(tuple(sys.version_info[:3]))
    return _create_prerequisite("python", "ok", f"{running} (floor {_format_version(PYTHON_FLOOR)})")


def _check_git(runtime) -> dict:
    try:
        version = read_git_version(runtime.run_process)
    except ToolNotFound:
        return _create_prerequisite("git", "finding", "not on PATH")
    return _create_prerequisite("git", "ok", f"{version} (no floor)")


def _read_release(version: str):
    try:
        return tuple(int(part) for part in version.split(".")[: len(AWAWA_FLOOR)])
    except ValueError:
        return None


def _check_awawa(runtime) -> dict:
    floor = _format_version(AWAWA_FLOOR)
    try:
        version = read_awawa_version(runtime.run_process)
    except ToolNotFound:
        return _create_prerequisite("awawa", "finding", f"not on PATH (floor {floor})")
    release = _read_release(version)
    state = "ok" if release is not None and release >= AWAWA_FLOOR else "finding"
    return _create_prerequisite("awawa", state, f"{version} (floor {floor})")


def _check_scheduler(runtime) -> dict:
    try:
        record = runtime.run_process(
            ProcessRequest(
                argv=("systemctl", "--user", "is-system-running"),
                cwd=PROBE_DIRECTORY,
                timeout_s=PROBE_TIMEOUT_S,
                acceptable_exit_codes=EVERY_EXIT_CODE,
            )
        )
    except ToolNotFound:
        return _create_optional("scheduler", "warning", "systemctl not on PATH", SCHEDULER_FALLBACK)
    systemd_state = record.stdout.strip().partition("\n")[0]
    if systemd_state in SYSTEMD_STATES_FIT_FOR_TIMERS:
        return _create_optional("scheduler", "ok", f"user systemd instance {systemd_state}", SCHEDULER_FALLBACK)
    return _create_optional("scheduler", "warning", f"no user systemd instance ({systemd_state})", SCHEDULER_FALLBACK)


def _check_forge(runtime) -> dict:
    forge = resolve_plugin("forge", "github")
    try:
        account = forge.describe_account({"schema_version": 1}, runtime)
    except ToolNotFound:
        return _create_optional("forge", "warning", "gh not on PATH", FORGE_FALLBACK)
    if account["login"] is None:
        return _create_optional("forge", "warning", "gh logged in to no account", FORGE_FALLBACK)
    return _create_optional("forge", "ok", f"gh as {account['login']}", FORGE_FALLBACK)


def _check_awawa_web(runtime) -> dict:
    try:
        runtime.run_process(ProcessRequest(argv=("awawa-web", "--help"), cwd=PROBE_DIRECTORY, timeout_s=PROBE_TIMEOUT_S))
    except ToolNotFound:
        return _create_optional("awawa-web", "warning", "not on PATH", AWAWA_WEB_FALLBACK)
    return _create_optional("awawa-web", "ok", "on PATH", AWAWA_WEB_FALLBACK)


def run(request, runtime) -> dict:
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "items": [
            _check_python(),
            _check_git(runtime),
            _check_awawa(runtime),
            _check_scheduler(runtime),
            _check_forge(runtime),
            _check_awawa_web(runtime),
        ],
    }
