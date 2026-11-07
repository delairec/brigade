from dataclasses import dataclass

from brigade.corpus.read_entities import Entity
from brigade.runtime import Runtime
from brigade.system.parse_configuration import Configuration


@dataclass(frozen=True)
class BranchPreflightDemand:
    project: Entity
    task: str
    task_branch: str
    base_branch: str
    configuration: Configuration


def preflight_task_branch(runtime: Runtime, demand: BranchPreflightDemand) -> dict:
    raise NotImplementedError("preflight_task_branch")
