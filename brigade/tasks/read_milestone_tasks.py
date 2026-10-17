from collections.abc import Callable
from pathlib import Path

from brigade.corpus.read_entities import Entity, read_entities
from brigade.system.run_process import ProcessRecord, ProcessRequest

TASK_TYPE = "TASK"


def read_milestone_tasks(
    run_process: Callable[[ProcessRequest], ProcessRecord], root: Path, milestone: str
) -> tuple[Entity, ...]:
    return read_entities(run_process, root, TASK_TYPE, f"MILESTONE==@MILESTONE.{milestone}")
