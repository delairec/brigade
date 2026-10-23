from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.git.timeouts import REMOTE_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest

REMOTE = "origin"


@dataclass(frozen=True)
class BranchesFetch:
    repository: Path
    branches: tuple[str, ...]
    environment: dict


def fetch_branches(run_process: Callable[[ProcessRequest], ProcessRecord], fetch: BranchesFetch) -> None:
    run_process(
        ProcessRequest(
            argv=("git", "fetch", "--quiet", REMOTE, *fetch.branches),
            cwd=str(fetch.repository),
            timeout_s=REMOTE_TIMEOUT_S,
            environment=fetch.environment,
        )
    )
