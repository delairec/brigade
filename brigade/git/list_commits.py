from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from brigade.git.timeouts import TREE_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest

RECORD_SEPARATOR = "\x1e"
FIELD_SEPARATOR = "\x1f"
LOG_FORMAT = "%x1e%H%x1f%an%x1f%at%x1f%s"
LINE_SEPARATOR = "\n"


@dataclass(frozen=True)
class Commit:
    sha: str
    author: str
    date: datetime
    subject: str
    files: tuple[str, ...]


def _parse_record(record: str) -> Commit:
    header, *lines = record.split(LINE_SEPARATOR)
    sha, author, timestamp, subject = header.split(FIELD_SEPARATOR)
    return Commit(
        sha=sha,
        author=author,
        date=datetime.fromtimestamp(int(timestamp), UTC),
        subject=subject,
        files=tuple(line for line in lines if line),
    )


def list_commits(
    run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path, since: date
) -> tuple[Commit, ...]:
    output = run_process(
        ProcessRequest(
            argv=(
                "git",
                "log",
                f"--since={since.isoformat()} 00:00:00 +0000",
                f"--format={LOG_FORMAT}",
                "--name-only",
                "HEAD",
                "--",
            ),
            cwd=str(repository),
            timeout_s=TREE_TIMEOUT_S,
        )
    )
    return tuple(_parse_record(part) for part in output.stdout.split(RECORD_SEPARATOR)[1:])
