from pathlib import Path
from string import Template

from brigade.command import Command
from brigade.corpus.shipped_data import SHIPPED_DATA, SHIPPED_SCHEMA
from brigade.errors import BrigadeError, CannotWrite
from brigade.git.commit_files import CommitRequest, commit_files
from brigade.git.create_repository import create_repository
from brigade.git.read_git_identity import read_git_identity
from brigade.runtime import Runtime

DOCUMENT_SCHEMA_VERSION = 1
GITIGNORE_FILE = ".gitignore"
GITIGNORE_CONTENT = "config.toml\n"
COMMIT_MESSAGE = "brigade init: the operational corpus"
SCHEMA_COMMIT_MESSAGE = "brigade init: the shipped schema"
STATE_WIDTH = 9
NAME_WIDTH = 13
STATES = ("created", "present", "replaced", "differs")


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
    try:
        config_root.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise CannotWrite(error.filename or config_root, error) from error
    create_repository(runtime.run_process, config_root)
    return {**item, "state": "created"}


def _render_configuration(runtime: Runtime) -> str:
    template = Template((SHIPPED_DATA / "config.toml.tpl").read_text(encoding="utf-8"))
    return template.substitute(state_root=runtime.paths.state_root, cache_root=runtime.paths.cache_root)


def _write_file(path: Path, content: bytes) -> None:
    try:
        path.write_bytes(content)
    except OSError as error:
        raise CannotWrite(error.filename or path, error) from error


def _ensure_file(name: str, path: Path, content: bytes, *, replace_differing: bool) -> dict:
    item = {"name": name, "path": str(path)}
    if not path.exists():
        _write_file(path, content)
        return {**item, "state": "created"}
    if path.read_bytes() == content:
        return {**item, "state": "present"}
    if replace_differing:
        _write_file(path, content)
        return {**item, "state": "replaced"}
    return {**item, "state": "differs"}


def _commit(runtime: Runtime, file_names: tuple[str, ...], message: str) -> None:
    if file_names:
        commit_files(
            runtime.run_process,
            CommitRequest(repository=runtime.paths.config_root, files=file_names, message=message),
        )


def _render_item(item: dict) -> str:
    return f"{item['state']:<{STATE_WIDTH}}{item['name']:<{NAME_WIDTH}}{item['path']}"


def _summarise(items: list[dict]) -> str:
    counts = " · ".join(f"{state} {sum(1 for item in items if item['state'] == state)}" for state in STATES)
    return f"init: {counts}"


def _warn(item: dict) -> str:
    return f"warning: {item['name']} differs from the shipped file and is left as it is"


def _render_text(document: dict) -> str:
    items = document["items"]
    lines = [
        *(_render_item(item) for item in items),
        "",
        _summarise(items),
        *(_warn(item) for item in items if item["state"] == "differs"),
    ]
    return "\n".join(lines)


def _read_request(options):
    return options


def _decide_exit_code(document: dict) -> int:
    return 0


def init(request, runtime: Runtime) -> dict:
    _require_identity(runtime)
    repository = _ensure_repository(runtime)
    gitignore = runtime.paths.config_root / GITIGNORE_FILE
    shipped_files = [
        ("schema", runtime.paths.schema_file, SHIPPED_SCHEMA.read_bytes()),
        (".gitignore", gitignore, GITIGNORE_CONTENT.encode("utf-8")),
        ("config.toml", runtime.paths.configuration_file, _render_configuration(runtime).encode("utf-8")),
    ]
    committed_files = (runtime.paths.schema_file, gitignore)
    file_items = [
        _ensure_file(name, path, content, replace_differing=path == runtime.paths.schema_file)
        for name, path, content in shipped_files
    ]
    states = {path: item["state"] for (_, path, _), item in zip(shipped_files, file_items, strict=True)}
    _commit(runtime, tuple(path.name for path in committed_files if states[path] == "created"), COMMIT_MESSAGE)
    _commit(
        runtime,
        tuple(path.name for path in committed_files if states[path] == "replaced"),
        SCHEMA_COMMIT_MESSAGE,
    )
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, "items": [repository, *file_items]}


COMMAND = Command(
    path=("init",),
    help="create the operational corpus repository, its schema and config.toml",
    run=init,
    read_request=_read_request,
    render_text=_render_text,
    decide_exit_code=_decide_exit_code,
)
