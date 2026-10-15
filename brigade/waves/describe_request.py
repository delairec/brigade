from brigade.corpus.read_entity import Entity
from brigade.registry.read_project_field import read_project_field

PROJECT_PREFIX = "@PROJECT."


def describe_request(request: Entity) -> dict:
    return {
        "name": request.name,
        "project": read_project_field(request, "PROJECT").removeprefix(PROJECT_PREFIX),
        "status": read_project_field(request, "STATUS"),
        "milestone": read_project_field(request, "MILESTONE"),
        "branch": read_project_field(request, "BRANCH"),
        "created_at": read_project_field(request, "CREATED_AT"),
    }
