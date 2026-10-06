from brigade.registry.find_project import find_project
from brigade.registry.read_projects import read_projects
from brigade.registry.require_operational_corpus import require_operational_corpus

DOCUMENT_SCHEMA_VERSION = 1


def project_show(request, runtime) -> dict:
    require_operational_corpus(runtime.paths.config_root)
    project = find_project(read_projects(runtime), request.name)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "project": {
            "name": project.name,
            "fields": [{"name": field.name, "value": field.value} for field in project.fields],
        },
    }
