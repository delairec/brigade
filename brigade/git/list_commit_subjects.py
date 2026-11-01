from collections.abc import Callable
from pathlib import Path

from brigade.git.timeouts import GIT_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest


def list_commit_subjects(
    run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path, base: str, head: str
) -> tuple[str, ...]:
    record = run_process(
        ProcessRequest(
            argv=("git", "log", "--reverse", "--format=%s", f"{base}..{head}", "--"),
            cwd=str(repository),
            timeout_s=GIT_TIMEOUT_S,
        )
    )
    return tuple(record.stdout.splitlines())
