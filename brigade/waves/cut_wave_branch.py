from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.read_entities import Entity
from brigade.git.cut_branch import BranchCut, cut_branch
from brigade.git.find_branch import find_branch
from brigade.git.push_branch import BranchPush, push_branch
from brigade.registry.is_on_github import is_on_github
from brigade.registry.read_project_field import read_project_field
from brigade.system.parse_configuration import CLI_KEY
from brigade.system.run_process import ProcessRecord, ProcessRequest
from brigade.waves.locate_project_main import locate_project_main


@dataclass(frozen=True)
class WaveBranchCut:
    project: Entity
    branch: str
    read_environment: Callable[[str], dict]


def cut_wave_branch(run_process: Callable[[ProcessRequest], ProcessRecord], cut: WaveBranchCut) -> None:
    repository = Path(read_project_field(cut.project, "PATH"))
    if not find_branch(run_process, repository, cut.branch):
        start = locate_project_main(run_process, cut.project, cut.read_environment)
        cut_branch(run_process, BranchCut(repository=repository, branch=cut.branch, start=start))
    if is_on_github(cut.project):
        push = BranchPush(repository=repository, branch=cut.branch, environment=cut.read_environment(CLI_KEY))
        push_branch(run_process, push)
