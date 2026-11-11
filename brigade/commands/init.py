import argparse
from pathlib import Path
from string import Template

from brigade.command import Argument, Command
from brigade.corpus.shipped_data import SHIPPED_DATA, SHIPPED_SCHEMA
from brigade.errors import BrigadeError, ToolFailure
from brigade.git.add_origin import add_origin
from brigade.git.commit_files import CommitRequest, commit_files
from brigade.git.create_repository import create_repository
from brigade.git.read_git_identity import read_git_identity
from brigade.git.read_origin_url import read_origin_url
from brigade.registry.read_projects import read_projects
from brigade.runtime import Runtime
from brigade.system.create_directory import create_directory
from brigade.system.find_answering_clients import find_answering_clients
from brigade.system.find_installed_scheduler import find_installed_scheduler
from brigade.system.parse_configuration import parse_configuration
from brigade.system.write_bytes_file import write_bytes_file

DOCUMENT_SCHEMA_VERSION = 1
GITIGNORE_FILE = ".gitignore"
GITIGNORE_CONTENT = "config.toml\n"
COMMIT_MESSAGE = "brigade init: the operational corpus"
STATE_WIDTH = 9
NAME_WIDTH = 13
STATES = ("created", "present", "differs")
COMMENTED_CLIENT_LINE = '# client = ""'
DOCTOR_STEP = "brigade doctor"
PROJECT_STEP = "brigade project add <path>"
SCHEDULER_STEP = "brigade scheduler install"
STEP_INDENT = "  "


def _require_identity(runtime: Runtime) -> None:
    identity = read_git_identity(runtime.run_process)
    missing = [key for key, value in (("user.name", identity.name), ("user.email", identity.email)) if value is None]
    if missing:
        raise BrigadeError(f"the git identity lacks {' and '.join(missing)}; set it with git config --global")


def _ensure_repository(runtime: Runtime) -> dict:
    config_root = runtime.paths.config_root
    item = {"name": "repository", "path": str(config_root)}
    if (config_root / ".git").exists():
        return {**item, "state": "present"}
    create_directory(config_root)
    create_repository(runtime.run_process, config_root)
    return {**item, "state": "created"}


def _ensure_remote(url: str, runtime: Runtime) -> dict:
    config_root = runtime.paths.config_root
    item = {"name": "remote", "path": url}
    origin = read_origin_url(runtime.run_process, config_root)
    if origin == url:
        return {**item, "state": "present"}
    if origin is not None:
        raise BrigadeError(
            f"the origin of {config_root} is {origin}; set it with git -C {config_root} remote set-url origin {url}"
        )
    add_origin(runtime.run_process, config_root, url)
    return {**item, "state": "created"}


def _write_client_line(clients: tuple[str, ...]) -> str:
    if len(clients) == 1:
        return f'client = "{clients[0]}"'
    return COMMENTED_CLIENT_LINE


def _render_configuration(runtime: Runtime, clients: tuple[str, ...]) -> str:
    template = Template((SHIPPED_DATA / "config.toml.tpl").read_text(encoding="utf-8"))
    return template.substitute(
        state_root=runtime.paths.state_root,
        cache_root=runtime.paths.cache_root,
        client_line=_write_client_line(clients),
    )


def _read_configured_client(runtime: Runtime) -> str | None:
    try:
        return parse_configuration(runtime.paths.configuration_file).client
    except BrigadeError:
        return None


def _has_projects(runtime: Runtime) -> bool:
    try:
        return bool(read_projects(runtime))
    except ToolFailure:
        return False


def _list_steps(client: str | None, runtime: Runtime) -> list[str]:
    client_step = [] if client is not None else [f"set the client key in {runtime.paths.configuration_file}"]
    project_step = [] if _has_projects(runtime) else [PROJECT_STEP]
    scheduler_step = [] if find_installed_scheduler(runtime)[1].installed else [SCHEDULER_STEP]
    return [DOCTOR_STEP, *client_step, *project_step, *scheduler_step]


def _ensure_file(name: str, path: Path, content: bytes) -> dict:
    item = {"name": name, "path": str(path)}
    if not path.is_file():
        write_bytes_file(path, content)
        return {**item, "state": "created"}
    if path.read_bytes() == content:
        return {**item, "state": "present"}
    return {**item, "state": "differs"}


def _render_item(item: dict) -> str:
    return f"{item['state']:<{STATE_WIDTH}}{item['name']:<{NAME_WIDTH}}{item['path']}"


def _summarise(items: list[dict]) -> str:
    counts = " · ".join(f"{state} {sum(1 for item in items if item['state'] == state)}" for state in STATES)
    return f"init: {counts}"


def _warn(item: dict) -> str:
    return f"warning: {item['name']} differs from the shipped file and is left as it is"


def _describe_clients(document: dict) -> list[str]:
    if document["client"] is not None:
        return []
    clients = document["clients"]
    found = f"{', '.join(clients)} answer their probe" if clients else "no supported client answers its probe"
    return [f"client: {found}; the client key is left commented"]


def _render_text(document: dict) -> str:
    items = document["items"]
    lines = [
        *(_render_item(item) for item in items),
        "",
        _summarise(items),
        *(_warn(item) for item in items if item["state"] == "differs"),
        *_describe_clients(document),
        "",
        "next steps:",
        *(f"{STEP_INDENT}{step}" for step in document["steps"]),
    ]
    return "\n".join(lines)


def init(request: argparse.Namespace, runtime: Runtime) -> dict:
    _require_identity(runtime)
    repository = _ensure_repository(runtime)
    remote = [] if request.remote is None else [_ensure_remote(request.remote, runtime)]
    clients = find_answering_clients(runtime)
    gitignore = runtime.paths.config_root / GITIGNORE_FILE
    shipped_files = [
        ("schema", runtime.paths.schema_file, SHIPPED_SCHEMA.read_bytes()),
        (".gitignore", gitignore, GITIGNORE_CONTENT.encode("utf-8")),
        ("config.toml", runtime.paths.configuration_file, _render_configuration(runtime, clients).encode("utf-8")),
    ]
    committed_files = (runtime.paths.schema_file, gitignore)
    file_items = [_ensure_file(name, path, content) for name, path, content in shipped_files]
    created_to_commit = tuple(
        path.name
        for (_, path, _), item in zip(shipped_files, file_items, strict=True)
        if path in committed_files and item["state"] == "created"
    )
    if created_to_commit:
        commit_files(
            runtime.run_process,
            CommitRequest(repository=runtime.paths.config_root, files=created_to_commit, message=COMMIT_MESSAGE),
        )
    client = _read_configured_client(runtime)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "items": [repository, *remote, *file_items],
        "clients": list(clients),
        "client": client,
        "steps": _list_steps(client, runtime),
    }


COMMAND = Command(
    path=("init",),
    help="create the operational corpus repository, its schema and config.toml",
    run=init,
    render_text=_render_text,
    arguments=(Argument(("--remote",), {"help": "the url set as origin of the configuration repository"}),),
)
