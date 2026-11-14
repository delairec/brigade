import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.collecting.read_stale_worktrees import STALE_BRANCH, StaleWorktreesReading, read_stale_worktrees
from brigade.corpus.read_entities import Entity
from brigade.errors import BrigadeError
from brigade.git.check_ancestor import check_ancestor
from brigade.git.has_local_changes import has_local_changes
from brigade.git.is_on_a_remote import is_on_a_remote
from brigade.git.list_worktrees import Worktree, list_worktrees
from brigade.git.read_branch_head import read_branch_head
from brigade.git.resolve_commit import resolve_commit
from brigade.registry.read_project_field import read_project_field
from brigade.runs.is_run_live_on import is_run_live_on
from brigade.system.run_process import ProcessRecord, ProcessRequest


@dataclass(frozen=True)
class LeftoverFacts:
    project: str
    branch: str | None
    worktree: str | None
    head: str
    reached_forge: bool
    run_live: bool
    locked: bool
    uncommitted: bool
    main_checkout: bool

    def to_document(self) -> dict:
        return {
            "project": self.project,
            "branch": self.branch,
            "worktree": self.worktree,
            "head": self.head,
            "reached_forge": self.reached_forge,
            "run_live": self.run_live,
            "locked": self.locked,
            "uncommitted": self.uncommitted,
            "main_checkout": self.main_checkout,
        }


@dataclass(frozen=True)
class LeftoverReading:
    projects: tuple[Entity, ...]
    excluded_branches: frozenset[tuple[str, str]]
    state_root: Path
    is_alive: Callable[[Path], bool]
    read_stale_branches: Callable[[Entity], list[dict]]


@dataclass(frozen=True)
class _ProjectReading:
    run_process: Callable[[ProcessRequest], ProcessRecord]
    reading: LeftoverReading
    project: Entity
    repository: Path


@dataclass(frozen=True)
class _Guards:
    run_live: bool
    locked: bool
    uncommitted: bool


DESCENDING = 0
NO_GUARD = _Guards(run_live=False, locked=False, uncommitted=False)


def _read_guards(project_reading: _ProjectReading, worktree: Worktree | None) -> _Guards:
    if worktree is None:
        return NO_GUARD
    reading = project_reading.reading
    return _Guards(
        run_live=is_run_live_on(reading.state_root, worktree.path, reading.is_alive),
        locked=worktree.locked,
        uncommitted=worktree.path.is_dir() and has_local_changes(project_reading.run_process, worktree.path),
    )


def _is_within_pull_request(project_reading: _ProjectReading, head: str, pull_request: dict) -> bool:
    run_process = project_reading.run_process
    repository = project_reading.repository
    if resolve_commit(run_process, repository, pull_request["head_sha"]) is None:
        return False
    return check_ancestor(run_process, repository, head, pull_request["head_sha"]).exit_code == DESCENDING


def _has_reached_forge(project_reading: _ProjectReading, head: str, pull_requests: list[dict]) -> bool:
    within_a_pull_request = any(
        _is_within_pull_request(project_reading, head, pull_request) for pull_request in pull_requests
    )
    return within_a_pull_request or is_on_a_remote(project_reading.run_process, project_reading.repository, head)


def _read_stale_branch(project_reading: _ProjectReading, worktrees: tuple[Worktree, ...], stale: dict) -> LeftoverFacts:
    head = read_branch_head(project_reading.run_process, project_reading.repository, stale["branch"])
    worktree = next((worktree for worktree in worktrees if worktree.branch == stale["branch"]), None)
    guards = _read_guards(project_reading, worktree)
    return LeftoverFacts(
        project=project_reading.project.name,
        branch=stale["branch"],
        worktree=None if worktree is None else str(worktree.path),
        head=head,
        reached_forge=_has_reached_forge(project_reading, head, stale["pull_requests"]),
        run_live=guards.run_live,
        locked=guards.locked,
        uncommitted=guards.uncommitted,
        main_checkout=worktree is worktrees[0],
    )


def _read_stale_worktree(project_reading: _ProjectReading, worktree: Worktree) -> LeftoverFacts:
    guards = _read_guards(project_reading, worktree)
    return LeftoverFacts(
        project=project_reading.project.name,
        branch=None,
        worktree=str(worktree.path),
        head=worktree.head,
        reached_forge=is_on_a_remote(project_reading.run_process, project_reading.repository, worktree.head),
        run_live=guards.run_live,
        locked=guards.locked,
        uncommitted=guards.uncommitted,
        main_checkout=False,
    )


def _read_project_leftovers(project_reading: _ProjectReading) -> tuple[LeftoverFacts, ...]:
    reading = project_reading.reading
    stale = reading.read_stale_branches(project_reading.project)
    worktrees = list_worktrees(project_reading.run_process, project_reading.repository)
    branches = tuple(
        _read_stale_branch(project_reading, worktrees, item)
        for item in stale
        if (project_reading.project.name, item["branch"]) not in reading.excluded_branches
    )
    stale_worktrees = read_stale_worktrees(
        project_reading.run_process,
        StaleWorktreesReading(
            repository=project_reading.repository,
            stale_branches=tuple(item["branch"] for item in stale),
            state_root=reading.state_root,
            is_alive=reading.is_alive,
        ),
    )
    alone = tuple(
        _read_stale_worktree(project_reading, stale_worktree.worktree)
        for stale_worktree in stale_worktrees
        if stale_worktree.reason != STALE_BRANCH
    )
    return branches + alone


def _read_readable_leftovers(project_reading: _ProjectReading) -> tuple[LeftoverFacts, ...]:
    try:
        return _read_project_leftovers(project_reading)
    except BrigadeError as failure:
        sys.stderr.write(f"brigade tick: the leftovers of {project_reading.project.name} skipped: {failure}\n")
        return ()


def read_leftovers(
    run_process: Callable[[ProcessRequest], ProcessRecord], reading: LeftoverReading
) -> tuple[LeftoverFacts, ...]:
    return tuple(
        leftover
        for project in reading.projects
        for leftover in _read_readable_leftovers(
            _ProjectReading(
                run_process=run_process,
                reading=reading,
                project=project,
                repository=Path(read_project_field(project, "PATH")),
            )
        )
    )
