from collections.abc import Callable
from pathlib import Path

from brigade.corpus.read_entities import Entity
from brigade.git.fetch_branches import REMOTE, BranchesFetch, fetch_branches
from brigade.registry.is_on_github import is_on_github
from brigade.registry.read_project_field import read_project_field
from brigade.system.parse_configuration import CLI_KEY
from brigade.system.run_process import ProcessRecord, ProcessRequest


def locate_forge_branch(
    run_process: Callable[[ProcessRequest], ProcessRecord],
    project: Entity,
    branch: str,
    read_environment: Callable[[str], dict],
) -> str:
    if not is_on_github(project):
        return branch
    repository = Path(read_project_field(project, "PATH"))
    fetch_branches(
        run_process, BranchesFetch(repository=repository, branches=(branch,), environment=read_environment(CLI_KEY))
    )
    return f"{REMOTE}/{branch}"
