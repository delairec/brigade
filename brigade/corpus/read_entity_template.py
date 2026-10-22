from collections.abc import Callable
from pathlib import Path

from brigade.system.run_process import ProcessRecord, ProcessRequest

AWAWA_TIMEOUT_S = 30.0
TYPE_NOT_DECLARED = 1
TYPE_DECLARED_OR_NOT = (0, TYPE_NOT_DECLARED)


def read_entity_template(
    run_process: Callable[[ProcessRequest], ProcessRecord], root: Path, entity_type: str, name: str
) -> str | None:
    record = run_process(
        ProcessRequest(
            argv=("awawa", "new", entity_type, name, str(root)),
            cwd=str(root),
            timeout_s=AWAWA_TIMEOUT_S,
            acceptable_exit_codes=TYPE_DECLARED_OR_NOT,
        )
    )
    return None if record.exit_code == TYPE_NOT_DECLARED else record.stdout
