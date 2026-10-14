from dataclasses import dataclass

from brigade.errors import BrigadeError
from brigade.registry.read_project_field import read_project_field
from brigade.runtime import Runtime
from brigade.waves.read_wave_request import ENTITY_TYPE, read_wave_request

PLANNING_STATUS = "planning"
PROJECT_PREFIX = "@PROJECT."


@dataclass(frozen=True)
class PlanningRequest:
    name: str
    project: str
    text: str


def read_planning_request(runtime: Runtime, name: str) -> PlanningRequest:
    request = read_wave_request(runtime, name)
    status = read_project_field(request, "STATUS")
    if status != PLANNING_STATUS:
        raise BrigadeError(f"@{ENTITY_TYPE}.{name} is {status}, not {PLANNING_STATUS}")
    return PlanningRequest(
        name=name,
        project=read_project_field(request, "PROJECT").removeprefix(PROJECT_PREFIX),
        text=read_project_field(request, "TEXT"),
    )
