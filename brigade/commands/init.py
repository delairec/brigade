from importlib.resources import files
from string import Template

from brigade.command import Command
from brigade.errors import BrigadeError, CannotWrite
from brigade.git.commit_files import CommitRequest, commit_files
from brigade.git.create_repository import create_repository
from brigade.git.read_git_identity import read_git_identity
from brigade.runtime import Runtime

DOCUMENT_SCHEMA_VERSION = 1
SHIPPED_DATA = files("brigade.corpus") / "data"
SCHEMA_FILE = "_schema.awawa"
GITIGNORE_FILE = ".gitignore"
CONFIGURATION_FILE = "config.toml"
GITIGNORE_CONTENT = "config.toml\n"
COMMITTED_FILES = (SCHEMA_FILE, GITIGNORE_FILE)
COMMIT_MESSAGE = "brigade init: the operational corpus"
STATE_WIDTH = 9
NAME_WIDTH = 13
STATES = ("created", "present", "differs")


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


def _ensure_file(runtime: Runtime, name: str, file_name: str, content: bytes) -> dict:
    path = runtime.paths.config_root / file_name
    item = {"name": name, "path": str(path)}
    if not path.exists():
        try:
            path.write_bytes(content)
        except OSError as error:
            raise CannotWrite(error.filename or path, error) from error
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
    shipped_files = [
        ("schema", SCHEMA_FILE, (SHIPPED_DATA / "schema.awawa.tpl").read_bytes()),
        (".gitignore", GITIGNORE_FILE, GITIGNORE_CONTENT.encode("utf-8")),
        ("config.toml", CONFIGURATION_FILE, _render_configuration(runtime).encode("utf-8")),
    ]
    file_items = [_ensure_file(runtime, name, file_name, content) for name, file_name, content in shipped_files]
    created_to_commit = tuple(
        file_name
        for (_, file_name, _), item in zip(shipped_files, file_items, strict=True)
        if file_name in COMMITTED_FILES and item["state"] == "created"
    )
    if created_to_commit:
        commit_files(
            runtime.run_process,
            CommitRequest(repository=runtime.paths.config_root, files=created_to_commit, message=COMMIT_MESSAGE),
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
