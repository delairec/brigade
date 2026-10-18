from dataclasses import dataclass


@dataclass(frozen=True)
class StartWave:
    request: str


@dataclass(frozen=True)
class LaunchTask:
    request: str
    project: str
    milestone: str
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
class RunPreflight:
    project: str
    wave: str
    branch: str
    task: str
    pr: int


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
