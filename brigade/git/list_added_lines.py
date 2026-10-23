import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.git.timeouts import TREE_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest

NEW_FILE_PREFIX = "+++ b/"
ADDED_PREFIX = "+"
HUNK_HEADER = re.compile(r"@@ -\S+ \+(?P<start>\d+)(?:,(?P<count>\d+))? @@")
SINGLE_LINE = 1


@dataclass(frozen=True)
class AddedLine:
    path: str
    line: int
    text: str


def list_added_lines(
    run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path, start: str, end: str
) -> tuple[AddedLine, ...]:
    record = run_process(
        ProcessRequest(
            argv=(
                "git",
                "diff",
                "--unified=0",
                "--no-color",
                "--no-ext-diff",
                "--text",
                "--end-of-options",
                start,
                end,
                "--",
            ),
            cwd=str(repository),
            timeout_s=TREE_TIMEOUT_S,
        )
    )
    return _read_added_lines(record.stdout)


def _read_added_lines(diff: str) -> tuple[AddedLine, ...]:
    added = []
    path = ""
    line = 0
    remaining = 0
    for text in diff.splitlines():
        if remaining:
            if text.startswith(ADDED_PREFIX):
                added.append(AddedLine(path=path, line=line, text=text.removeprefix(ADDED_PREFIX)))
                line += 1
                remaining -= 1
            continue
        hunk = HUNK_HEADER.match(text)
        if text.startswith(NEW_FILE_PREFIX):
            path = text.removeprefix(NEW_FILE_PREFIX)
        elif hunk is not None:
            line = int(hunk["start"])
            remaining = int(hunk["count"] or SINGLE_LINE)
    return tuple(added)
