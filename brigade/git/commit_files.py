from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.system.run_process import ProcessRecord, ProcessRequest

READ_TIMEOUT_S = 10.0
COMMIT_TIMEOUT_S = 30.0
STAGED_UNCHANGED_OR_CHANGED = (0, 1)
STAGED_CHANGES_FOUND = 1


@dataclass(frozen=True)
class CommitRequest:
    repository: Path
    files: tuple[str, ...]
    message: str


def commit_files(run_process: Callable[[ProcessRequest], ProcessRecord], request: CommitRequest) -> None:
    cwd = str(request.repository)
    run_process(ProcessRequest(argv=("git", "add", "--", *request.files), cwd=cwd, timeout_s=READ_TIMEOUT_S))
    staged = run_process(
        ProcessRequest(
            argv=("git", "diff", "--cached", "--quiet", "--", *request.files),
            cwd=cwd,
            timeout_s=READ_TIMEOUT_S,
            acceptable_exit_codes=STAGED_UNCHANGED_OR_CHANGED,
        )
    )
    if staged.exit_code != STAGED_CHANGES_FOUND:
        return
    run_process(
        ProcessRequest(argv=("git", "commit", "--quiet", "-m", request.message), cwd=cwd, timeout_s=COMMIT_TIMEOUT_S)
    )
