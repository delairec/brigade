from collections.abc import Callable
from pathlib import Path

from brigade.corpus.run_awawa import run_awawa
from brigade.system.run_process import ProcessRecord, ProcessRequest

DECLARED = 0


def check_type_declared(run_process: Callable[[ProcessRequest], ProcessRecord], root: Path, entity_type: str) -> bool:
    record = run_awawa(run_process, root, ("show", entity_type, str(root)))
    return record.exit_code == DECLARED
