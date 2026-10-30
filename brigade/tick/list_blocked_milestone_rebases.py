from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.read_entities import Entity
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.milestone_branch_cut import MilestoneBranchCut
from brigade.ledger.run_finished import RunFinished
from brigade.registry.read_project_field import read_project_field
from brigade.runs.read_run_question import read_run_question
from brigade.waves.locate_branch_worktree import locate_branch_worktree

PATH_FIELD = "PATH"
BLOCKED_OUTCOME = "blocked"


@dataclass(frozen=True)
class BlockedMilestoneRebase:
    branch: str
    question: str


@dataclass(frozen=True)
class MilestoneRebasesReading:
    entries: tuple[LedgerEntry, ...]
    runs: tuple[dict, ...]
    projects: tuple[Entity, ...]
    worktree_root: str | None


def _read_blocked_question(reading: MilestoneRebasesReading, worktree: Path) -> str | None:
    naming = [run for run in reading.runs if run["worktree"] == str(worktree)]
    if not naming:
        return None
    finished = [
        entry.event
        for entry in reading.entries
        if isinstance(entry.event, RunFinished) and entry.event.run == naming[-1]["run"]
    ]
    if not finished or finished[-1].outcome != BLOCKED_OUTCOME:
        return None
    return read_run_question(finished[-1].message)


def list_blocked_milestone_rebases(reading: MilestoneRebasesReading) -> tuple[BlockedMilestoneRebase, ...]:
    blocked = []
    for project in reading.projects:
        repository = Path(read_project_field(project, PATH_FIELD))
        branches = {
            entry.event.branch
            for entry in reading.entries
            if isinstance(entry.event, MilestoneBranchCut) and entry.event.project == project.name
        }
        for branch in sorted(branches):
            question = _read_blocked_question(
                reading, locate_branch_worktree(repository, reading.worktree_root, branch)
            )
            if question is not None:
                blocked.append(BlockedMilestoneRebase(branch=branch, question=question))
    return tuple(blocked)
