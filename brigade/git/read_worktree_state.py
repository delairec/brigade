from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.git.list_changed_files import list_changed_files
from brigade.git.timeouts import GIT_TIMEOUT_S
from brigade.system.run_process import EVERY_EXIT_CODE, ProcessRecord, ProcessRequest

SUCCEEDED_EXIT_CODE = 0


@dataclass(frozen=True)
class ChangedFile:
    path: str
    size: int | None
    mtime_ns: int | None


@dataclass(frozen=True)
class WorktreeState:
    head: str
    changed: frozenset[ChangedFile]


def _describe_changed_file(toplevel: Path, path: str) -> ChangedFile:
    try:
        status = (toplevel / path).lstat()
    except FileNotFoundError:
        return ChangedFile(path=path, size=None, mtime_ns=None)
    return ChangedFile(path=path, size=status.st_size, mtime_ns=status.st_mtime_ns)


def read_worktree_state(
    run_process: Callable[[ProcessRequest], ProcessRecord], worktree: Path, progress_file: Path
) -> WorktreeState | None:
    record = run_process(
        ProcessRequest(
            argv=("git", "rev-parse", "--show-toplevel", "HEAD"),
            cwd=str(worktree),
            timeout_s=GIT_TIMEOUT_S,
            acceptable_exit_codes=EVERY_EXIT_CODE,
        )
    )
    if record.exit_code != SUCCEEDED_EXIT_CODE:
        return None
    toplevel, head = record.stdout.splitlines()
    changed = (path for path in list_changed_files(run_process, worktree) if Path(toplevel, path) != progress_file)
    return WorktreeState(head=head, changed=frozenset(_describe_changed_file(Path(toplevel), path) for path in changed))
