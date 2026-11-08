from pathlib import Path

from brigade.corpus.read_entity import Entity, read_entity
from brigade.errors import BrigadeError
from brigade.ledger.read_ledger import read_ledger
from brigade.registry.read_corpus_workspace import read_corpus_workspace
from brigade.registry.read_project_field import read_project_field
from brigade.runtime import Runtime
from brigade.waves.find_milestone_branch import find_milestone_branch
from brigade.waves.read_wave_milestone import read_wave_milestone

TASK_TYPE = "TASK"
MAIN_FIELD = "MAIN"


def find_task_base(runtime: Runtime, worktree: Path, project: Entity, task: str) -> str:
    milestone = read_wave_milestone(
        task, (read_entity(runtime.run_process, worktree / read_corpus_workspace(project), TASK_TYPE, task),)
    )
    if milestone is None:
        return read_project_field(project, MAIN_FIELD)
    entries = read_ledger(runtime.paths.state_root).entries
    branch = find_milestone_branch(entries, project.name, milestone)
    if branch is None:
        raise BrigadeError(f"@MILESTONE.{milestone} of @TASK.{task} has no branch in the ledger")
    return branch
