import sys
from pathlib import Path

from brigade.corpus.lint_corpus import lint_corpus
from brigade.corpus.read_awawa_version import read_awawa_version
from brigade.errors import BrigadeError, ToolFailure, ToolNotFound
from brigade.git.read_git_version import read_git_version
from brigade.python_floor import PYTHON_FLOOR
from brigade.system.ask_configured_client import ask_configured_client
from brigade.system.read_optional_configuration import read_optional_configuration
from brigade.system.read_user_systemd_state import SYSTEMD_STATES_FIT_FOR_TIMERS, read_user_systemd_state
from brigade.system.resolve_plugin import resolve_plugin
from brigade.system.run_process import ProcessRequest

DOCUMENT_SCHEMA_VERSION = 1
AWAWA_FLOOR = (2, 7)
PROBE_DIRECTORY = "/"
PROBE_TIMEOUT_S = 10.0
SCHEDULER_FALLBACK = "a cron line, or brigade tick --loop"
FORGE_FALLBACK = "local mode without a forge"
AWAWA_WEB_FALLBACK = "the dashboard's corpus view only"
INSTRUCTIONS_FALLBACK = "built-in roles and no instructions package"
CONFIGURATION_FILE = "config.toml"
STEPS_FALLBACK = "the wall-time limit of each run"
STEP_COUNT_FEATURE = "step_count"


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


def _check_client(runtime) -> dict:
    try:
        probe = ask_configured_client(runtime, "probe", {"schema_version": DOCUMENT_SCHEMA_VERSION})
    except BrigadeError as error:
        return _create_prerequisite("client", "finding", str(error))
    name = probe.client_name
    version_argv = probe.document["version_argv"]
    if version_argv is None:
        return _create_prerequisite("client", "ok", f"{name}: no client executable")
    try:
        record = runtime.run_process(
            ProcessRequest(argv=tuple(version_argv), cwd=PROBE_DIRECTORY, timeout_s=PROBE_TIMEOUT_S)
        )
    except ToolFailure as error:
        return _create_prerequisite("client", "finding", f"{name}: {error}")
    first_line = record.stdout.strip().partition("\n")[0]
    return _create_prerequisite("client", "ok", f"{name}: {first_line}")


def _check_scheduler(runtime) -> dict:
    try:
        systemd_state = read_user_systemd_state(runtime.run_process)
    except ToolNotFound:
        return _create_optional("scheduler", "warning", "systemctl not on PATH", SCHEDULER_FALLBACK)
    if systemd_state in SYSTEMD_STATES_FIT_FOR_TIMERS:
        return _create_optional("scheduler", "ok", f"user systemd instance {systemd_state}", SCHEDULER_FALLBACK)
    if not systemd_state:
        return _create_optional("scheduler", "warning", "no user systemd instance", SCHEDULER_FALLBACK)
    return _create_optional("scheduler", "warning", f"no user systemd instance ({systemd_state})", SCHEDULER_FALLBACK)


def _check_forge(runtime) -> dict:
    forge = resolve_plugin("forge", "github", runtime)
    try:
        account = forge.describe_account({"schema_version": 1}, runtime)
    except ToolNotFound:
        return _create_optional("forge", "warning", "gh not on PATH", FORGE_FALLBACK)
    if account["login"] is None:
        return _create_optional("forge", "warning", "gh logged in to no account", FORGE_FALLBACK)
    return _create_optional("forge", "ok", f"gh as {account['login']}", FORGE_FALLBACK)


def _check_awawa_web(runtime) -> dict:
    try:
        runtime.run_process(
            ProcessRequest(argv=("awawa-web", "--help"), cwd=PROBE_DIRECTORY, timeout_s=PROBE_TIMEOUT_S)
        )
    except ToolNotFound:
        return _create_optional("awawa-web", "warning", "not on PATH", AWAWA_WEB_FALLBACK)
    return _create_optional("awawa-web", "ok", "on PATH", AWAWA_WEB_FALLBACK)


def _describe_instructions(state: str, detail: str) -> dict:
    return _create_optional("instructions", state, detail, INSTRUCTIONS_FALLBACK)


def _check_instructions(runtime) -> dict:
    try:
        configuration = read_optional_configuration(runtime.paths.config_root / CONFIGURATION_FILE)
        if configuration.instructions is None:
            return _describe_instructions("warning", "none configured")
        report = lint_corpus(runtime.run_process, Path(configuration.instructions))
    except BrigadeError as error:
        return _describe_instructions("warning", str(error))
    if report.clean:
        return _describe_instructions("ok", f"lint --strict clean in {configuration.instructions}")
    return _describe_instructions("warning", f"lint --strict fails in {configuration.instructions}")


def _check_steps(runtime) -> list[dict]:
    try:
        probe = ask_configured_client(runtime, "probe", {"schema_version": DOCUMENT_SCHEMA_VERSION})
    except BrigadeError:
        return []
    if STEP_COUNT_FEATURE in probe.document["features"]:
        return []
    detail = f"{probe.client_name} counts no steps: the budget is held on the clock and the run cut at its limit"
    return [_create_optional("steps", "warning", detail, STEPS_FALLBACK)]


def doctor(request, runtime) -> dict:
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "items": [
            _check_python(),
            _check_git(runtime),
            _check_awawa(runtime),
            _check_client(runtime),
            _check_scheduler(runtime),
            _check_forge(runtime),
            _check_awawa_web(runtime),
            _check_instructions(runtime),
            *_check_steps(runtime),
        ],
    }
