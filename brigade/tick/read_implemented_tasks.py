from collections.abc import Callable
from pathlib import Path

from brigade.corpus.read_awawa_document import read_awawa_document
from brigade.system.run_process import ProcessRecord, ProcessRequest

TASK_TYPE = "TASK"


def read_implemented_tasks(run_process: Callable[[ProcessRequest], ProcessRecord], root: Path) -> tuple[str, ...]:
    status = read_awawa_document(run_process, root, ("status", TASK_TYPE, "--where", "STATUS==implemented"))
    return tuple(entity["name"] for entity in status["entities"])
