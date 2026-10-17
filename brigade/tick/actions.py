from dataclasses import dataclass


@dataclass(frozen=True)
class StartWave:
    request: str


@dataclass(frozen=True)
class LaunchTask:
    request: str
    project: str
    milestone: str
    branch: str
    task: str


@dataclass(frozen=True)
class LaunchStudy:
    study: str
