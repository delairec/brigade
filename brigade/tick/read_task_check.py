import json
from pathlib import Path

from brigade.tasks.locate_check_record import locate_check_record
from brigade.tick.head_proof import TaskCheck


def read_task_check(state_root: Path, project: str, task: str) -> TaskCheck | None:
    record = locate_check_record(state_root, project, task)
    if not record.exists():
        return None
    document = json.loads(record.read_text(encoding="utf-8"))
    return TaskCheck(
        head=document["head"],
        failed_commands=tuple(check["command"] for check in document["checks"] if not check["passed"]),
    )
