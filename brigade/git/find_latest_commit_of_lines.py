import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.git.timeouts import GIT_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest

BLAME_HEADER = re.compile(r"([0-9a-f]{40}) ")
COMMITTER_TIME = "committer-time "


@dataclass(frozen=True)
class LinesOfFile:
    repository: Path
    path: str
    first: int
    last: int


def find_latest_commit_of_lines(run_process: Callable[[ProcessRequest], ProcessRecord], lines: LinesOfFile) -> str:
    record = run_process(
        ProcessRequest(
            argv=("git", "blame", "--porcelain", "-L", f"{lines.first},{lines.last}", "HEAD", "--", lines.path),
            cwd=str(lines.repository),
            timeout_s=GIT_TIMEOUT_S,
        )
    )
    times = {}
    commit = None
    for line in record.stdout.splitlines():
        header = BLAME_HEADER.match(line)
        if header:
            commit = header.group(1)
        elif line.startswith(COMMITTER_TIME):
            times[commit] = int(line.removeprefix(COMMITTER_TIME))
    return max(times, key=times.get)
