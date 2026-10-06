from brigade.corpus.read_entities import Entity
from brigade.registry.read_projects import read_projects
from brigade.registry.require_operational_corpus import require_operational_corpus

DOCUMENT_SCHEMA_VERSION = 1
NO_VALUE = ""


def _read_field(project: Entity, name: str) -> str:
    return next((field.value for field in project.fields if field.name == name), NO_VALUE)


def project_list(request, runtime) -> dict:
    require_operational_corpus(runtime.paths.config_root)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "projects": [
            {"name": project.name, "path": _read_field(project, "PATH"), "status": _read_field(project, "STATUS")}
            for project in read_projects(runtime)
        ],
    }
