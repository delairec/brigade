from pathlib import Path
from typing import Callable, Optional

from brigade.system.run_process import ProcessRecord, ProcessRequest

RESOLVE_TIMEOUT_S = 10.0
RESOLVED_OR_NOT = (0, 1)
COMMIT_PEEL = "^{commit}"


def resolve_commit(
    run_process: Callable[[ProcessRequest], ProcessRecord], repository: Path, ref: str
) -> Optional[str]:
    record = run_process(
        ProcessRequest(
            argv=("git", "rev-parse", "--verify", "--quiet", "--end-of-options", f"{ref}{COMMIT_PEEL}"),
            cwd=str(repository),
            timeout_s=RESOLVE_TIMEOUT_S,
            acceptable_exit_codes=RESOLVED_OR_NOT,
        )
    )
    return record.stdout.strip() or None
