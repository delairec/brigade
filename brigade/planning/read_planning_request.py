from dataclasses import dataclass

from brigade.corpus.read_entity import read_entity
from brigade.errors import BrigadeError, EntityNotDefined
from brigade.registry.read_project_field import read_project_field
from brigade.registry.require_operational_corpus import require_operational_corpus
from brigade.runtime import Runtime

ENTITY_TYPE = "REQUEST"
PLANNING_STATUS = "planning"
PROJECT_PREFIX = "@PROJECT."


@dataclass(frozen=True)
class PlanningRequest:
    name: str
    project: str
    text: str


def read_planning_request(runtime: Runtime, name: str) -> PlanningRequest:
    require_operational_corpus(runtime.paths)
    try:
        request = read_entity(runtime.run_process, runtime.paths.config_root, ENTITY_TYPE, name)
    except EntityNotDefined:
        raise BrigadeError(f"@{ENTITY_TYPE}.{name} is not defined in the operational corpus") from None
    status = read_project_field(request, "STATUS")
    if status != PLANNING_STATUS:
        raise BrigadeError(f"@{ENTITY_TYPE}.{name} is {status}, not {PLANNING_STATUS}")
    return PlanningRequest(
        name=name,
        project=read_project_field(request, "PROJECT").removeprefix(PROJECT_PREFIX),
        text=read_project_field(request, "TEXT"),
    )
