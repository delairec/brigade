from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.git.timeouts import GIT_TIMEOUT_S
from brigade.system.run_process import ProcessRecord, ProcessRequest


@dataclass(frozen=True)
class BranchCut:
    repository: Path
    branch: str
    start: str


def cut_branch(run_process: Callable[[ProcessRequest], ProcessRecord], cut: BranchCut) -> None:
    run_process(
        ProcessRequest(
            argv=("git", "branch", "--quiet", cut.branch, cut.start), cwd=str(cut.repository), timeout_s=GIT_TIMEOUT_S
        )
    )
