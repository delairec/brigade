import sys
from pathlib import Path

from brigade.command import Command
from brigade.corpus.lint_corpus import lint_corpus
from brigade.corpus.read_awawa_version import read_awawa_version
from brigade.errors import BrigadeError, ToolFailure, ToolNotFound
from brigade.git.read_git_version import read_git_version
from brigade.python_floor import PYTHON_FLOOR
from brigade.runtime import Runtime
from brigade.system.ask_forge_account import ask_forge_account
from brigade.system.ask_login_environment import ask_login_environment
from brigade.system.ask_named_client import ask_named_client
from brigade.system.client_question import ClientQuestion
from brigade.system.probe_answer import ProbeAnswer
from brigade.system.probe_request import ProbeRequest
from brigade.system.read_configuration import CLI_KEY, Configuration, ConfigurationMissing, read_configuration
from brigade.system.read_user_systemd_state import SYSTEMD_STATES_FIT_FOR_TIMERS, read_user_systemd_state
from brigade.system.require_configured_client import require_configured_client
from brigade.system.run_process import ProcessRequest

DOCUMENT_SCHEMA_VERSION = 1
AWAWA_FLOOR = (2, 7)
PROBE_DIRECTORY = "/"
PROBE_TIMEOUT_S = 10.0
SCHEDULER_FALLBACK = "a cron line, or brigade tick --loop"
FORGE_FALLBACK = "local mode without a forge"
FORGE_NAME = "github"
FORGE_LOGIN_FALLBACK = "the commands acting as it stop"
UNBOUND_ENVIRONMENT = {}
NO_FORGE_ACCOUNTS = {}
AWAWA_WEB_FALLBACK = "the dashboard's corpus view only"
INSTRUCTIONS_FALLBACK = "built-in roles and no instructions package"
NO_INSTRUCTIONS = "none configured"
STEPS_FALLBACK = "the wall-time limit of each run"
STEP_COUNT_FEATURE = "step_count"
STATE_WIDTH = 9
NAME_WIDTH = 13
DETAIL_WIDTH = 36


def _format_version(version: tuple[int, ...]) -> str:
    return ".".join(str(part) for part in version)


def _create_prerequisite(name: str, state: str, detail: str) -> dict:
    return {"name": name, "kind": "prerequisite", "state": state, "detail": detail, "fallback": None}


def _create_optional(name: str, state: str, detail: str, fallback: str) -> dict:
    return {"name": name, "kind": "optional", "state": state, "detail": detail, "fallback": fallback}


def _check_python() -> dict:
    running = _format_version(tuple(sys.version_info[:3]))
    return _create_prerequisite("python", "ok", f"{running} (floor {_format_version(PYTHON_FLOOR)})")


def _check_git(runtime: Runtime) -> dict:
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


def _check_awawa(runtime: Runtime) -> dict:
    floor = _format_version(AWAWA_FLOOR)
    try:
        version = read_awawa_version(runtime.run_process)
    except ToolNotFound:
        return _create_prerequisite("awawa", "finding", f"not on PATH (floor {floor})")
    release = _read_release(version)
    state = "ok" if release is not None and release >= AWAWA_FLOOR else "finding"
    return _create_prerequisite("awawa", state, f"{version} (floor {floor})")


def _read_configuration(runtime: Runtime) -> Configuration | BrigadeError:
    try:
        return read_configuration(runtime.paths.configuration_file)
    except BrigadeError as error:
        return error


def _accept_configuration(reading: Configuration | BrigadeError) -> Configuration:
    if isinstance(reading, BrigadeError):
        raise reading
    return reading


def _probe_configured_client(reading: Configuration | BrigadeError, runtime: Runtime) -> tuple[str, ProbeAnswer]:
    configured = require_configured_client(_accept_configuration(reading), runtime.paths.configuration_file)
    client = runtime.resolve_plugin("client", configured.name)
    question = ClientQuestion(configured.name, ProbeRequest())
    return configured.name, ask_named_client(client, question, configured.configuration, runtime)


def _check_client(reading: Configuration | BrigadeError, runtime: Runtime) -> dict:
    try:
        name, probe = _probe_configured_client(reading, runtime)
    except BrigadeError as error:
        return _create_prerequisite("client", "finding", str(error))
    version_argv = probe.version_argv
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


def _check_scheduler(runtime: Runtime) -> dict:
    try:
        systemd_state = read_user_systemd_state(runtime.run_process)
    except ToolNotFound:
        return _create_optional("scheduler", "warning", "systemctl not on PATH", SCHEDULER_FALLBACK)
    if systemd_state in SYSTEMD_STATES_FIT_FOR_TIMERS:
        return _create_optional("scheduler", "ok", f"user systemd instance {systemd_state}", SCHEDULER_FALLBACK)
    if not systemd_state:
        return _create_optional("scheduler", "warning", "no user systemd instance", SCHEDULER_FALLBACK)
    return _create_optional("scheduler", "warning", f"no user systemd instance ({systemd_state})", SCHEDULER_FALLBACK)


def _read_forge_accounts(reading: Configuration | BrigadeError) -> dict:
    if isinstance(reading, BrigadeError):
        return NO_FORGE_ACCOUNTS
    return reading.forge_accounts


def _check_forge(reading: Configuration | BrigadeError, runtime: Runtime) -> dict:
    forge = runtime.resolve_plugin("forge", FORGE_NAME)
    login = _read_forge_accounts(reading).get(CLI_KEY)
    try:
        environment = UNBOUND_ENVIRONMENT if login is None else ask_login_environment(forge, FORGE_NAME, login, runtime)
        if environment is None:
            return _create_optional("forge", "warning", f"gh printed no token for {login}", FORGE_FALLBACK)
        account = ask_forge_account(forge, FORGE_NAME, environment, runtime)
    except ToolNotFound:
        return _create_optional("forge", "warning", "gh not on PATH", FORGE_FALLBACK)
    if account.login is None:
        return _create_optional("forge", "warning", "gh logged in to no account", FORGE_FALLBACK)
    return _create_optional("forge", "ok", f"gh as {account.login}", FORGE_FALLBACK)


def _group_keys_by_login(forge_accounts: dict) -> dict:
    keys_by_login = {}
    for key, login in forge_accounts.items():
        keys_by_login.setdefault(login, []).append(key)
    return keys_by_login


def _describe_forge_login(state: str, detail: str) -> dict:
    return _create_optional("forge login", state, detail, FORGE_LOGIN_FALLBACK)


def _check_forge_login(forge, login: str, keys: list[str], runtime: Runtime) -> dict:
    bound = ", ".join(keys)
    try:
        environment = ask_login_environment(forge, FORGE_NAME, login, runtime)
    except ToolNotFound:
        return _describe_forge_login("warning", f"gh not on PATH for {login}, bound to {bound}")
    if environment is None:
        return _describe_forge_login("warning", f"gh printed no token for {login}, bound to {bound}")
    return _describe_forge_login("ok", f"{login} for {bound}")


def _check_forge_logins(reading: Configuration | BrigadeError, runtime: Runtime) -> list[dict]:
    forge = runtime.resolve_plugin("forge", FORGE_NAME)
    keys_by_login = _group_keys_by_login(_read_forge_accounts(reading))
    return [_check_forge_login(forge, login, keys, runtime) for login, keys in keys_by_login.items()]


def _check_awawa_web(runtime: Runtime) -> dict:
    try:
        runtime.run_process(
            ProcessRequest(argv=("awawa-web", "--help"), cwd=PROBE_DIRECTORY, timeout_s=PROBE_TIMEOUT_S)
        )
    except ToolNotFound:
        return _create_optional("awawa-web", "warning", "not on PATH", AWAWA_WEB_FALLBACK)
    return _create_optional("awawa-web", "ok", "on PATH", AWAWA_WEB_FALLBACK)


def _describe_instructions(state: str, detail: str) -> dict:
    return _create_optional("instructions", state, detail, INSTRUCTIONS_FALLBACK)


def _check_instructions(reading: Configuration | BrigadeError, runtime: Runtime) -> dict:
    if isinstance(reading, ConfigurationMissing):
        return _describe_instructions("warning", NO_INSTRUCTIONS)
    try:
        configuration = _accept_configuration(reading)
        if configuration.instructions is None:
            return _describe_instructions("warning", NO_INSTRUCTIONS)
        report = lint_corpus(runtime.run_process, Path(configuration.instructions))
    except BrigadeError as error:
        return _describe_instructions("warning", str(error))
    if report.clean:
        return _describe_instructions("ok", f"lint --strict clean in {configuration.instructions}")
    return _describe_instructions("warning", f"lint --strict fails in {configuration.instructions}")


def _check_steps(reading: Configuration | BrigadeError, runtime: Runtime) -> list[dict]:
    try:
        name, probe = _probe_configured_client(reading, runtime)
    except BrigadeError:
        return []
    if STEP_COUNT_FEATURE in probe.features:
        return []
    detail = f"{name} counts no steps: the budget is held on the clock and the run cut at its limit"
    return [_create_optional("steps", "warning", detail, STEPS_FALLBACK)]


def _check_configuration(reading: Configuration | BrigadeError) -> list[dict]:
    if isinstance(reading, BrigadeError):
        return []
    return [_create_prerequisite("config", "finding", finding) for finding in reading.findings]


def _render_prerequisite(item: dict) -> str:
    return f"{item['state']:<{STATE_WIDTH}}{item['name']:<{NAME_WIDTH}}{item['detail']}"


def _render_optional(item: dict) -> str:
    label = "else" if item["state"] == "ok" else "fallback"
    columns = f"{item['state']:<{STATE_WIDTH}}{item['name']:<{NAME_WIDTH}}{item['detail']:<{DETAIL_WIDTH - 1}}"
    return f"{columns} {label}: {item['fallback']}"


def _summarise(prerequisites: list[dict], optional_items: list[dict]) -> str:
    prerequisites_ok = sum(1 for item in prerequisites if item["state"] == "ok")
    on_fallback = sum(1 for item in optional_items if item["state"] != "ok")
    optional_phrase = "optional item on its fallback" if on_fallback == 1 else "optional items on their fallback"
    return f"doctor: {prerequisites_ok} of {len(prerequisites)} prerequisites ok · {on_fallback} {optional_phrase}"


def _render_text(document: dict) -> str:
    prerequisites = [item for item in document["items"] if item["kind"] == "prerequisite"]
    optional_items = [item for item in document["items"] if item["kind"] == "optional"]
    lines = [
        "prerequisites",
        *(_render_prerequisite(item) for item in prerequisites),
        "optional",
        *(_render_optional(item) for item in optional_items),
        "",
        _summarise(prerequisites, optional_items),
    ]
    return "\n".join(lines)


def _read_request(options):
    return options


def _decide_exit_code(document: dict) -> int:
    if any(item["state"] == "finding" for item in document["items"]):
        return 1
    return 0


def doctor(request, runtime: Runtime) -> dict:
    reading = _read_configuration(runtime)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "items": [
            _check_python(),
            _check_git(runtime),
            _check_awawa(runtime),
            _check_client(reading, runtime),
            _check_scheduler(runtime),
            _check_forge(reading, runtime),
            *_check_forge_logins(reading, runtime),
            _check_awawa_web(runtime),
            _check_instructions(reading, runtime),
            *_check_steps(reading, runtime),
            *_check_configuration(reading),
        ],
    }


COMMAND = Command(
    path=("doctor",),
    help="check the prerequisites and report the optional items with their fallback",
    run=doctor,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
