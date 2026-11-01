from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.read_entities import Entity
from brigade.git.find_remote_branch import RemoteBranch, find_remote_branch
from brigade.registry.is_on_github import is_on_github
from brigade.registry.read_project_field import read_project_field
from brigade.system.parse_configuration import CLI_KEY
from brigade.system.run_process import ProcessRecord, ProcessRequest


@dataclass(frozen=True)
class RecordedMilestoneBranch:
    project: Entity
    branch: str
    read_environment: Callable[[str], dict]


def is_milestone_branch_off_the_forge(
    run_process: Callable[[ProcessRequest], ProcessRecord], recorded: RecordedMilestoneBranch
) -> bool:
    if not is_on_github(recorded.project):
        return False
    remote_branch = RemoteBranch(
        repository=Path(read_project_field(recorded.project, "PATH")),
        branch=recorded.branch,
        environment=recorded.read_environment(CLI_KEY),
    )
    return not find_remote_branch(run_process, remote_branch)
