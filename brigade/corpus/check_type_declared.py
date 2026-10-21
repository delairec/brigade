from collections.abc import Callable
from pathlib import Path

from brigade.system.run_process import EVERY_EXIT_CODE, ProcessRecord, ProcessRequest

AWAWA_TIMEOUT_S = 30.0
DECLARED = 0


def check_type_declared(run_process: Callable[[ProcessRequest], ProcessRecord], root: Path, entity_type: str) -> bool:
    record = run_process(
        ProcessRequest(
            argv=("awawa", "show", entity_type, str(root)),
            cwd=str(root),
            timeout_s=AWAWA_TIMEOUT_S,
            acceptable_exit_codes=EVERY_EXIT_CODE,
        )
    )
    return record.exit_code == DECLARED
