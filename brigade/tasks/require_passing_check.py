import json

from brigade.errors import BrigadeError
from brigade.git.resolve_commit import resolve_commit
from brigade.runtime import Runtime
from brigade.tasks.locate_check_record import locate_check_record
from brigade.tasks.locate_task_worktree import TaskWorktree

HEAD = "HEAD"


def require_passing_check(runtime: Runtime, worktree: TaskWorktree) -> dict:
    target = f"@TASK.{worktree.task}"
    record = locate_check_record(runtime.paths.state_root, worktree.project.name, worktree.task)
    if not record.exists():
        raise BrigadeError(f"no check of {target} is recorded; run brigade task check")
    check = json.loads(record.read_text(encoding="utf-8"))
    head = resolve_commit(runtime.run_process, worktree.path, HEAD)
    if check["head"] != head:
        raise BrigadeError(
            f"the last check of {target} is of {check['head']}, not of HEAD {head}; run brigade task check"
        )
    failing = next((entry["command"] for entry in check["checks"] if not entry["passed"]), None)
    if failing is not None:
        raise BrigadeError(f"the last check of {target} failed on {failing}; run brigade task check")
    return check
