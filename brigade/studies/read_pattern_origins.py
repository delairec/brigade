from brigade.corpus.read_entities import read_entities
from brigade.registry.read_project_field import read_project_field
from brigade.runtime import Runtime

PATTERN_REFERENCE_PREFIX = "@PATTERN."


def read_pattern_origins(runtime: Runtime, project: str) -> list[dict]:
    root = runtime.paths.config_root
    requests = [
        request
        for request in read_entities(runtime.run_process, root, "REQUEST")
        if read_project_field(request, "PROJECT") == f"@PROJECT.{project}" and read_project_field(request, "FROM")
    ]
    if not requests:
        return []
    titles = {
        f"{PATTERN_REFERENCE_PREFIX}{pattern.name}": read_project_field(pattern, "TITLE")
        for pattern in read_entities(runtime.run_process, root, "PATTERN")
    }
    constraints = {
        read_project_field(constraint, "FROM"): constraint.name
        for constraint in read_entities(runtime.run_process, root, "CONSTRAINT")
    }
    return [
        {
            "milestone": read_project_field(request, "MILESTONE"),
            "pattern": read_project_field(request, "FROM").removeprefix(PATTERN_REFERENCE_PREFIX),
            "constraint": constraints.get(read_project_field(request, "FROM")),
            "reason": titles[read_project_field(request, "FROM")],
        }
        for request in requests
    ]
