from collections.abc import Callable
from dataclasses import dataclass

from brigade.corpus.read_entities import Entity
from brigade.registry.is_on_a_forge import is_on_a_forge
from brigade.registry.read_project_field import read_project_field
from brigade.tick.head_proof import ForgeCheck

NO_FORGE_CHECK = ()


@dataclass(frozen=True)
class BranchHeadQuery:
    project: Entity
    branch: str
    commit: str
    list_check_runs: Callable[[str, str], list[dict]]


def read_branch_head_checks(query: BranchHeadQuery) -> tuple[ForgeCheck, ...]:
    if not is_on_a_forge(query.project):
        return NO_FORGE_CHECK
    return tuple(
        ForgeCheck(name=check_run["name"], verdict=check_run["conclusion"])
        for check_run in query.list_check_runs(read_project_field(query.project, "PATH"), query.branch)
        if check_run["head"] == query.commit
    )
