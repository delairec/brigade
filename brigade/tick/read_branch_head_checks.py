from collections.abc import Callable
from dataclasses import dataclass

from brigade.corpus.read_entities import Entity
from brigade.registry.is_on_github import GITHUB_FORGE, is_on_github
from brigade.registry.read_project_field import read_project_field
from brigade.runtime import Runtime
from brigade.system.ask_check_runs import CheckRunsQuery, ask_check_runs
from brigade.system.parse_configuration import CLI_KEY
from brigade.tick.head_proof import ForgeCheck

FORGE_KIND = "forge"
NO_FORGE_CHECK = ()


@dataclass(frozen=True)
class BranchHeadQuery:
    project: Entity
    branch: str
    commit: str
    read_environment: Callable[[str], dict]


def read_branch_head_checks(runtime: Runtime, query: BranchHeadQuery) -> tuple[ForgeCheck, ...]:
    if not is_on_github(query.project):
        return NO_FORGE_CHECK
    check_runs = ask_check_runs(
        runtime.resolve_plugin(FORGE_KIND, GITHUB_FORGE),
        GITHUB_FORGE,
        CheckRunsQuery(
            repository=read_project_field(query.project, "PATH"),
            branch=query.branch,
            environment=query.read_environment(CLI_KEY),
        ),
        runtime,
    )
    return tuple(
        ForgeCheck(name=check_run["name"], verdict=check_run["conclusion"])
        for check_run in check_runs
        if check_run["head"] == query.commit
    )
