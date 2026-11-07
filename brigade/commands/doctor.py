import argparse
import shlex
import shutil
import sys
from pathlib import Path

from brigade.command import Command
from brigade.corpus.lint_corpus import lint_corpus
from brigade.corpus.read_awawa_version import read_awawa_version
from brigade.corpus.read_entities import Entity, read_entities
from brigade.corpus.read_entity import read_entity
from brigade.corpus.shipped_data import SHIPPED_SCHEMA
from brigade.errors import BrigadeError, ToolFailure, ToolNotFound
from brigade.git.describe_checkout_lag import describe_checkout_lag
from brigade.git.find_branch import find_branch
from brigade.git.read_git_version import read_git_version
from brigade.python_floor import PYTHON_FLOOR
from brigade.registry.read_project_field import read_project_field
from brigade.registry.read_projects import read_projects
from brigade.roles.resolve_role import BUILT_IN_ROLESET, CORPUS_ROLESET, ROLE_FILE_PATTERN
from brigade.runtime import Runtime
from brigade.system.ask_forge_account import ask_forge_account
from brigade.system.ask_login_environment import ask_login_environment
from brigade.system.ask_named_client import ask_named_client
from brigade.system.choose_scheduler import choose_scheduler
from brigade.system.client_question import ClientQuestion
from brigade.system.describe_linger_warning import describe_linger_warning
from brigade.system.describe_slot_clients import describe_slot_clients
from brigade.system.find_awawa_web import find_awawa_web
from brigade.system.list_slot_clients_elsewhere import list_slot_clients_elsewhere
from brigade.system.parse_configuration import CLI_KEY, Configuration, ConfigurationMissing
from brigade.system.probe_answer import ProbeAnswer
from brigade.system.probe_request import ProbeRequest
from brigade.system.read_configuration import CONFIGURATION_REQUIRED, read_configuration
from brigade.system.read_user_systemd_state import SYSTEMD_STATES_FIT_FOR_TIMERS, read_user_systemd_state
from brigade.system.require_configured_client import require_configured_client
from brigade.system.run_process import ProcessRequest

DOCUMENT_SCHEMA_VERSION = 1
AWAWA_FLOOR = (2, 7)
PROBE_DIRECTORY = "/"
PROBE_TIMEOUT_S = 10.0
SCHEDULER_FALLBACK = "a cron line, or brigade tick --loop"
LINGER_FALLBACK = "the tick fires only while a session of the user is open"
FORGE_FALLBACK = "local mode without a forge"
FORGE_NAME = "github"
FORGE_LOGIN_FALLBACK = "the commands acting as it stop"
UNBOUND_ENVIRONMENT = {}
NO_FORGE_ACCOUNTS = {}
NO_SLOT_CLIENTS = {}
AWAWA_WEB_FALLBACK = "the dashboard's corpus view only"
INSTRUCTIONS_FALLBACK = "built-in roles and no instructions package"
NO_INSTRUCTIONS = "none configured"
STEPS_FALLBACK = "the wall-time limit of each run"
STEP_COUNT_FEATURE = "step_count"
CHECKOUT_FALLBACK = "git pull in the checkout"
SCHEMA_FALLBACK = "throw the operational corpus away, then run brigade init"
POLICY_TYPE = "POLICY"
PROJECT_PREFIX = "@PROJECT."
APPROVAL_REVIEW = "approval"
BUILD_SLOT = "build"
REVIEW_SLOT = "review"
REVIEW_FALLBACK = "GitHub refuses the approval of the review slot"
POLICIES_FALLBACK = "the review mode of each project unchecked"
AGENT_TYPE = "AGENT"
UNLOCATED_ROLESETS = (None, BUILT_IN_ROLESET, CORPUS_ROLESET)
PROJECT_COMMAND_FIELDS = ("SETUP", "ACCEPTANCE", "HEAVY")
PATH_SEPARATOR = "/"
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


def _attempt_configuration_reading(runtime: Runtime) -> Configuration | BrigadeError:
    try:
        return read_configuration(runtime, CONFIGURATION_REQUIRED)
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


def _check_linger(reading: Configuration | BrigadeError, runtime: Runtime) -> list[dict]:
    configured = None if isinstance(reading, BrigadeError) else reading.scheduler
    if choose_scheduler(configured, runtime.run_process).name != "systemd":
        return []
    warning = describe_linger_warning(runtime.run_process)
    if warning is None:
        return [_create_optional("linger", "ok", "the user systemd instance lingers", LINGER_FALLBACK)]
    return [_create_optional("linger", "warning", warning, LINGER_FALLBACK)]


def _is_unreadable(reading: Configuration | BrigadeError) -> bool:
    return isinstance(reading, BrigadeError) and not isinstance(reading, ConfigurationMissing)


def _read_forge_accounts(reading: Configuration | BrigadeError) -> dict:
    if isinstance(reading, BrigadeError):
        return NO_FORGE_ACCOUNTS
    return reading.forge_accounts


def _read_login_environment(forge, login: str, runtime: Runtime) -> dict | ToolNotFound | None:
    try:
        return ask_login_environment(forge, FORGE_NAME, login, runtime)
    except ToolNotFound as error:
        return error


def _check_forge(forge, login: str | None, environment: dict | ToolNotFound | None, runtime: Runtime) -> dict:
    if isinstance(environment, ToolNotFound):
        return _create_optional("forge", "warning", "gh not on PATH", FORGE_FALLBACK)
    if environment is None:
        return _create_optional("forge", "warning", f"gh printed no token for {login}", FORGE_FALLBACK)
    try:
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


def _check_forge_login(login: str, keys: list[str], environment: dict | ToolNotFound | None) -> dict:
    bound = ", ".join(keys)
    if isinstance(environment, ToolNotFound):
        return _describe_forge_login("warning", f"gh not on PATH for {login}, bound to {bound}")
    if environment is None:
        return _describe_forge_login("warning", f"gh printed no token for {login}, bound to {bound}")
    return _describe_forge_login("ok", f"{login} for {bound}")


def _check_forge_and_its_logins(reading: Configuration | BrigadeError, runtime: Runtime) -> list[dict]:
    if _is_unreadable(reading):
        return [
            _create_optional("forge", "warning", str(reading), FORGE_FALLBACK),
            _describe_forge_login("warning", str(reading)),
        ]
    forge = runtime.resolve_plugin("forge", FORGE_NAME)
    forge_accounts = _read_forge_accounts(reading)
    keys_by_login = _group_keys_by_login(forge_accounts)
    environments = {login: _read_login_environment(forge, login, runtime) for login in keys_by_login}
    cli_login = forge_accounts.get(CLI_KEY)
    cli_environment = UNBOUND_ENVIRONMENT if cli_login is None else environments[cli_login]
    return [
        _check_forge(forge, cli_login, cli_environment, runtime),
        *(_check_forge_login(login, keys, environments[login]) for login, keys in keys_by_login.items()),
    ]


def _has_distinct_build_and_review_logins(forge_accounts: dict) -> bool:
    build_login = forge_accounts.get(BUILD_SLOT)
    review_login = forge_accounts.get(REVIEW_SLOT)
    return build_login is not None and review_login is not None and build_login != review_login


def _warn_of_review_by_approval(policy) -> dict:
    project = read_project_field(policy, "PROJECT").removeprefix(PROJECT_PREFIX)
    detail = f"{project} reviews by approval without distinct logins for build and review"
    return _create_optional("review", "warning", detail, REVIEW_FALLBACK)


def _check_review_logins(reading: Configuration | BrigadeError, runtime: Runtime) -> list[dict]:
    if not runtime.paths.schema_file.exists():
        return []
    if _is_unreadable(reading):
        return [_create_optional("review", "warning", str(reading), POLICIES_FALLBACK)]
    if _has_distinct_build_and_review_logins(_read_forge_accounts(reading)):
        return []
    try:
        policies = read_entities(runtime.run_process, runtime.paths.config_root, POLICY_TYPE)
    except ToolFailure as error:
        return [_create_optional("review", "warning", f"POLICY unreadable: {error}", POLICIES_FALLBACK)]
    return [
        _warn_of_review_by_approval(policy)
        for policy in policies
        if read_project_field(policy, "REVIEW") == APPROVAL_REVIEW
    ]


def _check_awawa_web(runtime: Runtime) -> dict:
    if not find_awawa_web(runtime.run_process):
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


def _check_checkout(runtime: Runtime) -> list[dict]:
    detail = describe_checkout_lag(runtime.run_process, runtime.paths.package_file)
    if detail is None:
        return []
    return [_create_optional("checkout", "warning", detail, CHECKOUT_FALLBACK)]


def _check_schema(runtime: Runtime) -> list[dict]:
    schema = runtime.paths.schema_file
    if not schema.exists() or schema.read_bytes() == SHIPPED_SCHEMA.read_bytes():
        return []
    return [_create_optional("schema", "warning", f"{schema} differs from the shipped schema", SCHEMA_FALLBACK)]


def _check_configuration(reading: Configuration | BrigadeError) -> list[dict]:
    if isinstance(reading, BrigadeError):
        return []
    return [_create_prerequisite("config", "finding", finding) for finding in reading.findings]


def _report_findings(name: str, problems) -> list[dict]:
    return [_create_prerequisite(name, "finding", problem) for problem in problems]


def _find_slot_problems(slot: str, agent: str, configuration: Configuration, runtime: Runtime) -> list[str]:
    if configuration.instructions is None:
        file = runtime.paths.configuration_file
        return [f"slots.{slot} binds {agent} but no instructions corpus is set in {file}"]
    try:
        read_entity(runtime.run_process, Path(configuration.instructions), AGENT_TYPE, agent)
    except BrigadeError as error:
        return [f"slots.{slot}: {error}"]
    return []


def _check_slots(reading: Configuration | BrigadeError, runtime: Runtime) -> list[dict]:
    if isinstance(reading, BrigadeError):
        return []
    return _report_findings(
        "slots",
        (
            problem
            for slot, agent in reading.slots.items()
            for problem in _find_slot_problems(slot, agent, reading, runtime)
        ),
    )


def _find_client_problems(client: str, runtime: Runtime) -> list[str]:
    try:
        runtime.resolve_plugin("client", client)
    except BrigadeError as error:
        return [str(error)]
    return []


def _check_slot_clients(reading: Configuration | BrigadeError, runtime: Runtime) -> list[dict]:
    if isinstance(reading, BrigadeError):
        return []
    return _report_findings(
        "slot_clients",
        (
            f"slot_clients.{slot}: {problem}"
            for slot, client in reading.slot_clients.items()
            for problem in _find_client_problems(client, runtime)
        ),
    )


def _find_project_client_problems(client: str | None, runtime: Runtime) -> list[str]:
    if client is None:
        return []
    return _find_client_problems(client, runtime)


def _find_roleset_problems(roleset: str | None, checkout: Path) -> list[str]:
    if roleset in UNLOCATED_ROLESETS:
        return []
    directory = checkout / roleset
    if any(directory.glob(ROLE_FILE_PATTERN)):
        return []
    return [f"ROLESET {roleset} holds no role file in {directory}"]


def _find_main_problems(main: str, checkout: Path, runtime: Runtime) -> list[str]:
    try:
        found = find_branch(runtime.run_process, checkout, main)
    except ToolFailure as error:
        return [f"MAIN {main} cannot be read in {checkout}: {error}"]
    if found:
        return []
    return [f"MAIN {main} is not a branch of {checkout}"]


def _locate_program(word: str, checkout: Path) -> str:
    if PATH_SEPARATOR in word:
        return str(checkout / word)
    return word


def _find_command_problems(field_name: str, line: str, checkout: Path, search_path: str) -> list[str]:
    try:
        argv = shlex.split(line)
    except ValueError as error:
        return [f"{field_name} {line}: shlex.split refuses it, {error}"]
    if not argv:
        return [f"{field_name} is an empty line"]
    if shutil.which(_locate_program(argv[0], checkout), path=search_path) is None:
        return [f"{field_name} {line}: no executable {argv[0]}"]
    return []


def _read_values(project: Entity, field_name: str) -> list[str]:
    return [field.value for field in project.fields if field.name == field_name]


def _inspect_checkout(project: Entity, checkout: Path, runtime: Runtime) -> list[str]:
    search_path = runtime.paths.executable_search_path
    return [
        *_find_roleset_problems(read_project_field(project, "ROLESET"), checkout),
        *_find_main_problems(read_project_field(project, "MAIN"), checkout, runtime),
        *(
            problem
            for field_name in PROJECT_COMMAND_FIELDS
            for line in _read_values(project, field_name)
            for problem in _find_command_problems(field_name, line, checkout, search_path)
        ),
    ]


def _inspect_project(project: Entity, runtime: Runtime) -> list[str]:
    checkout = Path(read_project_field(project, "PATH"))
    located = (
        _inspect_checkout(project, checkout, runtime) if checkout.exists() else [f"PATH {checkout} does not exist"]
    )
    return [*_find_project_client_problems(read_project_field(project, "CLIENT"), runtime), *located]


def _check_projects(runtime: Runtime) -> list[dict]:
    if not runtime.paths.schema_file.exists():
        return []
    try:
        projects = read_projects(runtime)
    except ToolFailure as error:
        return _report_findings("project", [f"PROJECT unreadable: {error}"])
    return _report_findings(
        "project",
        (
            f"@PROJECT.{project.name}: {problem}"
            for project in projects
            for problem in _inspect_project(project, runtime)
        ),
    )


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
        *describe_slot_clients(document["slot_clients"]),
        "",
        _summarise(prerequisites, optional_items),
    ]
    return "\n".join(lines)


def _decide_exit_code(document: dict) -> int:
    if any(item["state"] == "finding" for item in document["items"]):
        return 1
    return 0


def _read_client(reading: Configuration | BrigadeError) -> str | None:
    return None if isinstance(reading, BrigadeError) else reading.client


def _read_slot_clients(reading: Configuration | BrigadeError) -> dict:
    return (
        NO_SLOT_CLIENTS if isinstance(reading, BrigadeError) else list_slot_clients_elsewhere(reading, reading.client)
    )


def doctor(request: argparse.Namespace, runtime: Runtime) -> dict:
    reading = _attempt_configuration_reading(runtime)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "client": _read_client(reading),
        "slot_clients": _read_slot_clients(reading),
        "items": [
            _check_python(),
            _check_git(runtime),
            _check_awawa(runtime),
            _check_client(reading, runtime),
            _check_scheduler(runtime),
            *_check_linger(reading, runtime),
            *_check_forge_and_its_logins(reading, runtime),
            *_check_review_logins(reading, runtime),
            _check_awawa_web(runtime),
            _check_instructions(reading, runtime),
            *_check_steps(reading, runtime),
            *_check_configuration(reading),
            *_check_slots(reading, runtime),
            *_check_slot_clients(reading, runtime),
            *_check_projects(runtime),
            *_check_checkout(runtime),
            *_check_schema(runtime),
        ],
    }


COMMAND = Command(
    path=("doctor",),
    help="check the prerequisites and report the optional items with their fallback",
    run=doctor,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
