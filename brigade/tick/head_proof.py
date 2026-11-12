from dataclasses import dataclass

from brigade.tick.commit_checks import CommitChecks

GREEN = "green"
RED = "red"
PENDING = "pending"
UNPROVEN = "unproven"


@dataclass(frozen=True)
class ForgeCheck:
    name: str
    verdict: str


@dataclass(frozen=True)
class HeadChecks:
    head: str
    checks: tuple[ForgeCheck, ...]


@dataclass(frozen=True)
class TaskCheck:
    head: str
    failed_commands: tuple[str, ...]


@dataclass(frozen=True)
class HeadEvidence:
    commit: str
    forge_checks: tuple[ForgeCheck, ...]
    task_check: TaskCheck | None
    commit_checks: CommitChecks | None


@dataclass(frozen=True)
class HeadProof:
    commit: str
    state: str
    failed_commands: tuple[str, ...]


@dataclass(frozen=True)
class HoldingHead:
    branch: str
    proof: HeadProof
