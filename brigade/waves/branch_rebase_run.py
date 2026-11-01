from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from brigade.corpus.read_entities import Entity


@dataclass(frozen=True)
class BranchRebaseRun:
    project: str
    worktree: Path
    branch: str
    base: str
    wave: str | None


class BranchRebaseGateways(Protocol):
    project: Entity
    worktree_root: str | None
    read_environment: Callable[[str], dict]
    is_run_live_on: Callable[[Path], bool]
    launch_rebase_run: Callable[[BranchRebaseRun], None]
