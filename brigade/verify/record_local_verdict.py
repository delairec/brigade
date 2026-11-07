from brigade.errors import BrigadeError
from brigade.git.read_current_branch import read_current_branch
from brigade.git.read_head import read_head
from brigade.ledger.append_event import append_event
from brigade.ledger.task_verdict import TaskVerdict
from brigade.runtime import Runtime
from brigade.tasks.locate_task_worktree import TaskWorktree

NO_PULL_REQUEST = None
NO_POSTED_REVIEW = None


def record_local_verdict(runtime: Runtime, worktree: TaskWorktree, verdict: dict) -> dict:
    head = read_head(runtime.run_process, worktree.path)
    judged = verdict["head"]
    if judged != head:
        branch = read_current_branch(runtime.run_process, worktree.path)
        raise BrigadeError(f"the verdict judged {judged}, no longer the head of {branch}, now {head}")
    event = TaskVerdict(
        project=worktree.project.name,
        wave=worktree.wave,
        task=worktree.task,
        pr=NO_PULL_REQUEST,
        head=head,
        verdict=verdict["verdict"],
        findings=tuple(verdict["findings"]),
        login=NO_POSTED_REVIEW,
    )
    append_event(runtime.paths, runtime.now, event)
    return event.to_document()
