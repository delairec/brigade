from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.git.timeouts import TREE_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest

COLUMN_SEPARATOR = "\t"


@dataclass(frozen=True)
class ChangedFile:
    path: str
    insertions: int
    deletions: int


def _parse_line(line: str) -> ChangedFile:
    insertions, deletions, path = line.split(COLUMN_SEPARATOR, 2)
    return ChangedFile(path=path, insertions=int(insertions), deletions=int(deletions))


def count_changed_lines(
    run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path, start: str, end: str
) -> tuple[ChangedFile, ...]:
    record = run_process(
        ProcessRequest(
            argv=("git", "diff", "--numstat", "--text", "--end-of-options", start, end, "--"),
            cwd=str(repository),
            timeout_s=TREE_TIMEOUT_S,
        )
    )
    return tuple(_parse_line(line) for line in record.stdout.splitlines())
