from dataclasses import dataclass


@dataclass(frozen=True)
class CommandResult:
    command: str
    exit_code: int


@dataclass(frozen=True)
class CommitChecks:
    project: str
    commit: str
    results: tuple[CommandResult, ...]
