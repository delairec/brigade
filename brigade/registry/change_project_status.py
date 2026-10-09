from brigade.errors import BrigadeError
from brigade.registry.change_registry import REGISTRY_FILE, change_registry
from brigade.registry.find_project import find_project
from brigade.registry.read_projects import read_projects
from brigade.registry.require_operational_corpus import require_operational_corpus
from brigade.registry.set_project_status import set_project_status
from brigade.runtime import Runtime

DOCUMENT_SCHEMA_VERSION = 1
ACTIONS = {"paused": "pause", "active": "resume"}


def _build_rewrite(runtime: Runtime, name: str, status: str):
    def rewrite(text: str) -> str | None:
        project = find_project(read_projects(runtime), name)
        if any(field.name == "STATUS" and field.value == status for field in project.fields):
            return None
        rewritten = set_project_status(text, name, status)
        if rewritten is None:
            raise BrigadeError(f"@PROJECT.{name} is not written in {REGISTRY_FILE}")
        return rewritten

    return rewrite


def change_project_status(runtime: Runtime, name: str, status: str) -> dict:
    require_operational_corpus(runtime.paths)
    changed = change_registry(
        runtime, f"brigade project {ACTIONS[status]}: {name}", _build_rewrite(runtime, name, status)
    )
    return {"schema_version": DOCUMENT_SCHEMA_VERSION, "project": name, "status": status, "changed": changed}
