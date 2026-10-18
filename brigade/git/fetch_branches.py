from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.system.run_process import ProcessRecord, ProcessRequest

FETCH_TIMEOUT_S = 120.0
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
            timeout_s=FETCH_TIMEOUT_S,
            environment=fetch.environment,
        )
    )
