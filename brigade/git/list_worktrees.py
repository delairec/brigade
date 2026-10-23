from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.git.timeouts import GIT_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest

RECORD_SEPARATOR = "\0\0"
LINE_SEPARATOR = "\0"
PATH_PREFIX = "worktree "
HEAD_PREFIX = "HEAD "
BRANCH_PREFIX = "branch refs/heads/"
BARE_LINE = "bare"
DETACHED_LINE = "detached"
LOCKED_WORD = "locked"
WORD_SEPARATOR = " "


@dataclass(frozen=True)
class Worktree:
    path: Path
    head: str
    branch: str | None
    detached: bool
    locked: bool


def _read_line(lines: list[str], prefix: str) -> str | None:
    return next((line[len(prefix) :] for line in lines if line.startswith(prefix)), None)


def _parse_record(record: str) -> Worktree | None:
    lines = record.split(LINE_SEPARATOR)
    if BARE_LINE in lines:
        return None
    return Worktree(
        path=Path(_read_line(lines, PATH_PREFIX)),
        head=_read_line(lines, HEAD_PREFIX),
        branch=_read_line(lines, BRANCH_PREFIX),
        detached=DETACHED_LINE in lines,
        locked=any(line.split(WORD_SEPARATOR, 1)[0] == LOCKED_WORD for line in lines),
    )


def list_worktrees(run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path) -> tuple[Worktree, ...]:
    record = run_process(
        ProcessRequest(
            argv=("git", "worktree", "list", "--porcelain", "-z"), cwd=str(repository), timeout_s=GIT_TIMEOUT_S
        )
    )
    records = (part.strip(LINE_SEPARATOR) for part in record.stdout.split(RECORD_SEPARATOR))
    worktrees = (_parse_record(part) for part in records if part)
    return tuple(worktree for worktree in worktrees if worktree is not None)
