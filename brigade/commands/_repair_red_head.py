import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from brigade.commands.run import run
from brigade.corpus.read_entities import Entity
from brigade.git.add_branch_worktree import BranchWorktree, add_branch_worktree
from brigade.git.add_worktree_on_branch import add_worktree_on_branch
from brigade.registry.read_project_field import read_project_field
from brigade.runs.find_head_repair import find_head_repair
from brigade.runtime import Runtime
from brigade.system.parse_configuration import Configuration
from brigade.tick.head_proof import RED, HoldingHead
from brigade.waves.locate_branch_worktree import locate_branch_worktree

REBASE_PROCEDURE = "rebase-on-base"
REBASE_SLOT = "rebase"


@dataclass(frozen=True)
class _Repair:
    branch: str
    arguments: tuple[str, ...]
    worktree: Path


def _plan_repair(configuration: Configuration, project: Entity, held_by: HoldingHead) -> _Repair:
    repository = Path(read_project_field(project, "PATH"))
    main = read_project_field(project, "MAIN")
    commit = held_by.proof.commit
    if held_by.branch != main:
        branch = held_by.branch
        arguments = (f"branch={branch}", f"head={commit}")
    else:
        branch = f"fix/repair-{main}-{commit}"
        arguments = (f"branch={branch}", f"head={commit}", f"into={main}")
    return _Repair(
        branch=branch,
        arguments=arguments,
        worktree=locate_branch_worktree(repository, configuration.worktree_root, branch),
    )


def _open_repair_worktree(runtime: Runtime, project: Entity, held_by: HoldingHead, repair: _Repair) -> None:
    if repair.worktree.exists():
        return
    repository = Path(read_project_field(project, "PATH"))
    if repair.branch == held_by.branch:
        add_worktree_on_branch(
            runtime.run_process,
            repository,
            BranchWorktree(path=repair.worktree, branch=repair.branch, start=held_by.proof.commit),
        )
        return
    add_branch_worktree(
        runtime.run_process,
        repository,
        BranchWorktree(path=repair.worktree, branch=repair.branch, start=held_by.proof.commit),
    )


def repair_red_head(runtime: Runtime, configuration: Configuration, project: Entity, held_by: HoldingHead) -> None:
    if held_by.proof.state != RED:
        return
    repair = _plan_repair(configuration, project, held_by)
    launched = find_head_repair(runtime.paths.state_root, repair.branch, held_by.proof.commit)
    if launched is not None:
        if launched.question is not None:
            sys.stderr.write(f"brigade tick: the repair of {held_by.branch} is blocked: {launched.question}\n")
        return
    _open_repair_worktree(runtime, project, held_by, repair)
    repairing = argparse.Namespace(
        procedure=configuration.procedures.get(REBASE_SLOT, REBASE_PROCEDURE),
        slot=REBASE_SLOT,
        project=project.name,
        cwd=str(repair.worktree),
        brief=None,
        arguments=repair.arguments,
        run_id=None,
        wave=None,
        task=None,
        detach=True,
        resume=False,
    )
    run(repairing, runtime)
