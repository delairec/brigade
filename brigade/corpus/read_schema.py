from collections.abc import Callable
from pathlib import Path

from brigade.system.run_process import ProcessRecord, ProcessRequest

AWAWA_TIMEOUT_S = 30.0
SCHEMA_NOT_DEFINED = 1
SHOWN_OR_NOT_DEFINED = (0, SCHEMA_NOT_DEFINED)


def read_schema(run_process: Callable[[ProcessRequest], ProcessRecord], root: Path, entity_type: str) -> str | None:
    record = run_process(
        ProcessRequest(
            argv=("awawa", "show", entity_type, str(root)),
            cwd=str(root),
            timeout_s=AWAWA_TIMEOUT_S,
            acceptable_exit_codes=SHOWN_OR_NOT_DEFINED,
        )
    )
    return None if record.exit_code == SCHEMA_NOT_DEFINED else record.stdout
