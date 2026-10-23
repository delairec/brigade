from collections.abc import Callable
from pathlib import Path

from brigade.git.find_branch import find_branch
from brigade.git.find_remote_branch import RemoteBranch, find_remote_branch
from brigade.registry.is_on_github import is_on_github
from brigade.registry.read_project_field import read_project_field
from brigade.system.parse_configuration import CLI_KEY
from brigade.system.run_process import ProcessRecord, ProcessRequest
from brigade.waves.cut_wave_branch import WaveBranchCut


def is_wave_branch_missing(run_process: Callable[[ProcessRequest], ProcessRecord], cut: WaveBranchCut) -> bool:
    repository = Path(read_project_field(cut.project, "PATH"))
    if not find_branch(run_process, repository, cut.branch):
        return True
    if not is_on_github(cut.project):
        return False
    remote_branch = RemoteBranch(repository=repository, branch=cut.branch, environment=cut.read_environment(CLI_KEY))
    return not find_remote_branch(run_process, remote_branch)
