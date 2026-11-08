import functools
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.read_entities import Entity
from brigade.errors import BrigadeError
from brigade.git.check_ancestor import check_ancestor
from brigade.git.list_worktrees import list_worktrees
from brigade.git.read_branch_head import read_branch_head
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.milestone_branch_cut import MilestoneBranchCut
from brigade.ledger.milestone_closed import MilestoneClosed
from brigade.ledger.wave_started import WaveStarted
from brigade.registry.read_project_field import read_project_field
from brigade.runs.is_run_live_on import is_run_live_on
from brigade.system.pull_request_facts import PullRequestFacts
from brigade.system.run_process import ProcessRecord, ProcessRequest
from brigade.waves.locate_branch_worktree import locate_branch_worktree
from brigade.waves.locate_forge_branch import locate_forge_branch
from brigade.waves.summarize_waves import ENDING_EVENTS

PATH_FIELD = "PATH"
MAIN_FIELD = "MAIN"
MERGED_PULL_REQUEST = "merged"
DESCENDING = 0
NO_WAVE = None
NO_MILESTONE = None


@dataclass(frozen=True)
class IntegrationBranchFacts:
    project: str
    branch: str
    milestone: str | None
    wave: str | None
    ended: bool
    merged_pull_request: int | None
    merged_head: str | None
    head: str
    reached_forge: bool
    worktree: str | None
    run_live: bool
    locked: bool

    def to_document(self) -> dict:
        return {
            "project": self.project,
            "branch": self.branch,
            "milestone": self.milestone,
            "wave": self.wave,
            "ended": self.ended,
            "merged_pull_request": self.merged_pull_request,
            "merged_head": self.merged_head,
            "head": self.head,
            "reached_forge": self.reached_forge,
            "worktree": self.worktree,
            "run_live": self.run_live,
            "locked": self.locked,
        }


@dataclass(frozen=True)
class IntegrationBranchReading:
    entries: tuple[LedgerEntry, ...]
    projects: tuple[Entity, ...]
    worktree_root: str | None
    state_root: Path
    read_pull_request: Callable[[str, str], PullRequestFacts | None]
    read_environment: Callable[[Entity, str], dict]
    locate_wave_base: Callable[[WaveStarted], str]
    is_alive: Callable[[Path], bool]


@dataclass(frozen=True)
class _RecordedBranch:
    project: str
    branch: str
    milestone: str | None
    started: WaveStarted | None
    ended: bool


def _list_recorded_branches(entries: tuple[LedgerEntry, ...]) -> list[_RecordedBranch]:
    events = [entry.event for entry in entries]
    closed = {(event.project, event.milestone) for event in events if isinstance(event, MilestoneClosed)}
    ended = {event.wave for event in events if isinstance(event, ENDING_EVENTS)}
    cuts = {(event.project, event.milestone): event for event in events if isinstance(event, MilestoneBranchCut)}
    milestone_branches = [
        _RecordedBranch(
            project=cut.project, branch=cut.branch, milestone=cut.milestone, started=NO_WAVE, ended=key in closed
        )
        for key, cut in cuts.items()
    ]
    wave_branches = [
        _RecordedBranch(
            project=event.project, branch=event.branch, milestone=NO_MILESTONE, started=event, ended=event.wave in ended
        )
        for event in events
        if isinstance(event, WaveStarted) and event.branch is not None
    ]
    return milestone_branches + wave_branches


@dataclass(frozen=True)
class _BranchReading:
    run_process: Callable[[ProcessRequest], ProcessRecord]
    reading: IntegrationBranchReading
    project: Entity
    repository: Path


def _is_within(branch_reading: _BranchReading, head: str, ref: str) -> bool:
    return check_ancestor(branch_reading.run_process, branch_reading.repository, head, ref).exit_code == DESCENDING


def _locate_base(branch_reading: _BranchReading, recorded: _RecordedBranch) -> str:
    if recorded.started is None:
        return read_project_field(branch_reading.project, MAIN_FIELD)
    return branch_reading.reading.locate_wave_base(recorded.started)


def _has_reached_forge(
    branch_reading: _BranchReading, recorded: _RecordedBranch, head: str, merged: PullRequestFacts | None
) -> bool:
    if merged is not None and _is_within(branch_reading, head, merged.head):
        return True
    base = locate_forge_branch(
        branch_reading.run_process,
        branch_reading.project,
        _locate_base(branch_reading, recorded),
        functools.partial(branch_reading.reading.read_environment, branch_reading.project),
    )
    return _is_within(branch_reading, head, base)


def _is_locked(branch_reading: _BranchReading, worktree: Path) -> bool:
    return any(
        listed.path == worktree and listed.locked
        for listed in list_worktrees(branch_reading.run_process, branch_reading.repository)
    )


def _read_merged_pull_request(branch_reading: _BranchReading, branch: str) -> PullRequestFacts | None:
    pull_request = branch_reading.reading.read_pull_request(str(branch_reading.repository), branch)
    if pull_request is None or pull_request.state != MERGED_PULL_REQUEST:
        return None
    return pull_request


def _read_branch(branch_reading: _BranchReading, recorded: _RecordedBranch) -> IntegrationBranchFacts | None:
    head = read_branch_head(branch_reading.run_process, branch_reading.repository, recorded.branch)
    if head is None:
        return None
    merged = _read_merged_pull_request(branch_reading, recorded.branch)
    reading = branch_reading.reading
    worktree = locate_branch_worktree(branch_reading.repository, reading.worktree_root, recorded.branch)
    return IntegrationBranchFacts(
        project=recorded.project,
        branch=recorded.branch,
        milestone=recorded.milestone,
        wave=None if recorded.started is None else recorded.started.wave,
        ended=recorded.ended,
        merged_pull_request=None if merged is None else merged.number,
        merged_head=None if merged is None else merged.head,
        head=head,
        reached_forge=_has_reached_forge(branch_reading, recorded, head, merged),
        worktree=str(worktree) if worktree.is_dir() else None,
        run_live=is_run_live_on(reading.state_root, worktree, reading.is_alive),
        locked=_is_locked(branch_reading, worktree),
    )


def _read_readable_branch(branch_reading: _BranchReading, recorded: _RecordedBranch) -> IntegrationBranchFacts | None:
    try:
        return _read_branch(branch_reading, recorded)
    except BrigadeError as failure:
        sys.stderr.write(f"brigade tick: the branch {recorded.branch} of {recorded.project} skipped: {failure}\n")
        return None


def read_integration_branches(
    run_process: Callable[[ProcessRequest], ProcessRecord], reading: IntegrationBranchReading
) -> tuple[IntegrationBranchFacts, ...]:
    projects = {project.name: project for project in reading.projects}
    readings = (
        (
            _BranchReading(
                run_process=run_process,
                reading=reading,
                project=projects[recorded.project],
                repository=Path(read_project_field(projects[recorded.project], PATH_FIELD)),
            ),
            recorded,
        )
        for recorded in _list_recorded_branches(reading.entries)
        if recorded.project in projects
    )
    return tuple(
        facts
        for facts in (_read_readable_branch(branch_reading, recorded) for branch_reading, recorded in readings)
        if facts is not None
    )
