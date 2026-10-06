from importlib.resources import files
from string import Template

from brigade.errors import BrigadeError
from brigade.git.commit_files import CommitRequest, commit_files
from brigade.git.create_repository import create_repository
from brigade.git.read_git_identity import read_git_identity

DOCUMENT_SCHEMA_VERSION = 1
SHIPPED_DATA = files("brigade.corpus") / "data"
SCHEMA_FILE = "_schema.awawa"
GITIGNORE_FILE = ".gitignore"
CONFIGURATION_FILE = "config.toml"
GITIGNORE_CONTENT = "config.toml\n"
COMMITTED_FILES = (SCHEMA_FILE, GITIGNORE_FILE)
COMMIT_MESSAGE = "brigade init: the operational corpus"


def _require_identity(runtime) -> None:
    identity = read_git_identity(runtime.run_process)
    missing = [key for key, value in (("user.name", identity.name), ("user.email", identity.email)) if value is None]
    if missing:
        raise BrigadeError(f"the git identity lacks {' and '.join(missing)}; set it with git config --global")


def _ensure_repository(runtime) -> dict:
    config_root = runtime.paths.config_root
    item = {"name": "repository", "path": str(config_root)}
    if (config_root / ".git").exists():
        return {**item, "state": "present"}
    config_root.mkdir(parents=True, exist_ok=True)
    create_repository(runtime.run_process, config_root)
    return {**item, "state": "created"}


def _render_configuration(runtime) -> str:
    template = Template((SHIPPED_DATA / "config.toml.tpl").read_text(encoding="utf-8"))
    return template.substitute(state_root=runtime.paths.state_root, cache_root=runtime.paths.cache_root)


def _ensure_file(runtime, name: str, file_name: str, content: bytes) -> dict:
    path = runtime.paths.config_root / file_name
    item = {"name": name, "path": str(path)}
    if not path.exists():
        path.write_bytes(content)
        return {**item, "state": "created"}
    if path.read_bytes() == content:
        return {**item, "state": "present"}
    return {**item, "state": "differs"}


def run(request, runtime) -> dict:
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
        for (_, file_name, _), item in zip(shipped_files, file_items)
        if file_name in COMMITTED_FILES and item["state"] == "created"
    )
    if created_to_commit:
        commit_files(
            runtime.run_process,
            CommitRequest(repository=runtime.paths.config_root, files=created_to_commit, message=COMMIT_MESSAGE),
        )
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, "items": [repository, *file_items]}
