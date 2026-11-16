from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.git.timeouts import GIT_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest


@dataclass(frozen=True)
class FileSince:
    repository: Path
    path: str
    since: str


def read_file_diff(run_process: Callable[[ProcessRequest], ProcessRecord], file: FileSince) -> str:
    record = run_process(
        ProcessRequest(
            argv=("git", "diff", "-U0", file.since, "HEAD", "--", file.path),
            cwd=str(file.repository),
            timeout_s=GIT_TIMEOUT_S,
        )
    )
    return record.stdout
