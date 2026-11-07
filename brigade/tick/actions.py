from dataclasses import dataclass

from brigade.ledger.task_pr_opened import TaskPrOpened
from brigade.studies.milestone_report_order import MilestoneReportOrder
from brigade.studies.task_report_order import TaskReportOrder
from brigade.tick.build_snapshot import PreflightFailure, TaskAmendment
from brigade.tick.head_proof import HeadChecks


@dataclass(frozen=True)
class LaunchTask:
    project: str
    wave: str
    branch: str
    task: str
    task_branch: str
    pull_request_checks: HeadChecks | None


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
class CarryOpenedPullRequest:
    wave: str
    opened: TaskPrOpened


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
    task_branch: str
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


@dataclass(frozen=True)
class CutMilestoneBranch:
    project: str
    milestone: str
    branch: str


@dataclass(frozen=True)
class StartWave:
    project: str
    milestone: str | None


@dataclass(frozen=True)
class ReportMilestone:
    order: MilestoneReportOrder


@dataclass(frozen=True)
class ReportTask:
    order: TaskReportOrder


@dataclass(frozen=True)
class CloseWave:
    wave: str
    project: str


@dataclass(frozen=True)
class CloseMilestone:
    project: str
    milestone: str
    pr: int


@dataclass(frozen=True)
class DescribeMilestonePullRequest:
    project: str
    milestone: str
    branch: str
    pr: int
    head: str


@dataclass(frozen=True)
class RebaseTask:
    project: str
    wave: str
    branch: str
    task: str
    task_branch: str
    pr: int
    worktree: str
    head: str
    holds_uncommitted_changes: bool


@dataclass(frozen=True)
class CollectCheckRuns:
    project: str


@dataclass(frozen=True)
class CollectReviewThreads:
    project: str


@dataclass(frozen=True)
class RebuildTask:
    project: str
    wave: str
    base: str
    task: str
    task_branch: str
    pr: int
    worktree: str
    reason: str
    amendment: TaskAmendment


@dataclass(frozen=True)
class RemoveIntegrationBranch:
    project: str
    branch: str
    worktree: str | None


@dataclass(frozen=True)
class KeepIntegrationBranch:
    project: str
    branch: str
    reason: str
