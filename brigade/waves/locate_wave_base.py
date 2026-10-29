from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.read_entities import Entity
from brigade.corpus.read_entity import read_entity
from brigade.registry.read_project_field import read_project_field
from brigade.runtime import Runtime
from brigade.waves.cut_milestone_branch import MilestoneBranchDemand, cut_milestone_branch

MILESTONE_TYPE = "MILESTONE"


@dataclass(frozen=True)
class WaveBaseDemand:
    project: Entity
    milestone: str | None
    root: Path
    read_environment: Callable[[str], dict]
    read_login: Callable[[], str]


def locate_wave_base(runtime: Runtime, demand: WaveBaseDemand) -> str:
    if demand.milestone is None:
        return read_project_field(demand.project, "MAIN")
    milestone = read_entity(runtime.run_process, demand.root, MILESTONE_TYPE, demand.milestone)
    return cut_milestone_branch(
        runtime,
        MilestoneBranchDemand(
            project=demand.project,
            milestone=milestone,
            read_environment=demand.read_environment,
            read_login=demand.read_login,
        ),
    )
