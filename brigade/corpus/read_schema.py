from collections.abc import Callable
from pathlib import Path

from brigade.corpus.run_awawa import run_awawa
from brigade.system.run_process import ProcessRecord, ProcessRequest

SCHEMA_NOT_DEFINED = 1
SHOWN_OR_NOT_DEFINED = (0, SCHEMA_NOT_DEFINED)


def read_schema(run_process: Callable[[ProcessRequest], ProcessRecord], root: Path, entity_type: str) -> str | None:
    record = run_awawa(run_process, root, ("show", entity_type, str(root)), SHOWN_OR_NOT_DEFINED)
    return None if record.exit_code == SCHEMA_NOT_DEFINED else record.stdout
