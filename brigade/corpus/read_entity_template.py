from collections.abc import Callable
from pathlib import Path

from brigade.corpus.run_awawa import run_awawa
from brigade.system.run_process import ProcessRecord, ProcessRequest

TYPE_NOT_DECLARED = 1
TYPE_DECLARED_OR_NOT = (0, TYPE_NOT_DECLARED)


def read_entity_template(
    run_process: Callable[[ProcessRequest], ProcessRecord], root: Path, entity_type: str, name: str
) -> str | None:
    record = run_awawa(run_process, root, ("new", entity_type, name, str(root)), TYPE_DECLARED_OR_NOT)
    return None if record.exit_code == TYPE_NOT_DECLARED else record.stdout
