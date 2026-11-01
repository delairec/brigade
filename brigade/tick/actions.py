from dataclasses import dataclass

from brigade.tick.build_snapshot import MergedWave, PreflightFailure


@dataclass(frozen=True)
class LaunchTask:
    project: str
    wave: str
    branch: str
    task: str


@dataclass(frozen=True)
class LaunchStudy:
    study: str


@dataclass(frozen=True)
class RecordTaskState:
    wave: str
    task: str
    state: str
    reason: str | None


@dataclass(frozen=True)
class ParkTask:
    wave: str
    task: str
    reason: str
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class RunPreflight:
    project: str
    wave: str
    branch: str
    task: str
    pr: int


@dataclass(frozen=True)
class LaunchVerification:
    project: str
    wave: str
    task: str
    pr: int
    worktree: str


@dataclass(frozen=True)
class LaunchRemediation:
    project: str
    wave: str
    task: str
    pr: int
    worktree: str


@dataclass(frozen=True)
class LaunchCheckRepair:
    project: str
    wave: str
    branch: str
    task: str
    pr: int
    worktree: str
    checks: tuple[str, ...]
    findings: tuple[PreflightFailure, ...]


@dataclass(frozen=True)
class MergePullRequest:
    project: str
    wave: str
    task: str
    pr: int
    method: str
    head: str


@dataclass(frozen=True)
class RemoveTaskWorktree:
    project: str
    task: str
    worktree: str


@dataclass(frozen=True)
class PauseWave:
    wave: str
    reason: str
    resume_at: str | None


@dataclass(frozen=True)
class ResumeWave:
    wave: str
    reason: str


@dataclass(frozen=True)
class ResumeTaskRun:
    wave: str
    task: str
    run: str
    state: str | None = None


@dataclass(frozen=True)
class RebaseMilestone:
    project: str
    milestone: str
    branch: str
    waves: tuple[str, ...]


@dataclass(frozen=True)
class CutMilestoneBranch:
    project: str
    milestone: str
    branch: str


@dataclass(frozen=True)
class RetargetWavePullRequest:
    project: str
    wave: str
    pr: int
    base: str


@dataclass(frozen=True)
class StartWave:
    project: str
    milestone: str | None


@dataclass(frozen=True)
class CutWaveBranch:
    project: str
    wave: str
    branch: str


@dataclass(frozen=True)
class ReportWave:
    wave: str


@dataclass(frozen=True)
class OpenIntegrationPullRequest:
    project: str
    wave: str
    branch: str
    tasks: tuple[str, ...]


@dataclass(frozen=True)
class MergeWavePullRequest:
    project: str
    wave: str
    pr: int
    method: str
    head: str


@dataclass(frozen=True)
class CloseWave:
    wave: str
    pr: int
    project: str
    milestones: tuple[str, ...]


@dataclass(frozen=True)
class OpenMilestonePullRequest:
    project: str
    milestone: str
    branch: str
    waves: tuple[MergedWave, ...]


@dataclass(frozen=True)
class CloseMilestone:
    project: str
    milestone: str
    pr: int


@dataclass(frozen=True)
class RebaseTask:
    project: str
    wave: str
    branch: str
    task: str
    pr: int
    worktree: str
    head: str
    parking_reason: str | None


@dataclass(frozen=True)
class CollectCheckRuns:
    project: str


@dataclass(frozen=True)
class CollectReviewThreads:
    project: str
