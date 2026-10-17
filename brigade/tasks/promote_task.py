from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.change_corpus_file import CorpusChange, change_corpus_file
from brigade.corpus.locate_corpus_lock import locate_corpus_lock
from brigade.corpus.locate_entity_block import locate_entity_block
from brigade.corpus.read_awawa_document import read_awawa_document
from brigade.errors import BrigadeError
from brigade.git.push_branch import BranchPush, push_branch
from brigade.git.read_current_branch import read_current_branch
from brigade.git.resolve_commit import resolve_commit
from brigade.ledger.append_event import append_event
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.task_pr_opened import TaskPrOpened
from brigade.ledger.task_promoted import TaskPromoted
from brigade.runtime import Runtime
from brigade.tasks.locate_task_worktree import TaskWorktree, locate_task_worktree

DOCUMENT_SCHEMA_VERSION = 1
HEAD = "HEAD"
TYPE_SEPARATOR = "|"
IMPLEMENTED = "implemented"
STATUS_LINE = "\tSTATUS "
DELIVERED_BY = "DELIVERED_BY"


@dataclass(frozen=True)
class TaskPromotionDemand:
    path: Path
    task: str | None
    pr: int | None
    environment: dict


def _read_recorded_pull_request(runtime: Runtime, worktree: TaskWorktree) -> int:
    opened = [
        entry.event.pr
        for entry in read_ledger(runtime.paths.state_root).entries
        if isinstance(entry.event, TaskPrOpened)
        and entry.event.project == worktree.project.name
        and entry.event.task == worktree.task
    ]
    if not opened:
        raise BrigadeError(f"no pull request of @TASK.{worktree.task} is recorded in the ledger; name it with --pr")
    return opened[-1]


def _refuse_undeclared(worktree: TaskWorktree, undeclared: str) -> BrigadeError:
    return BrigadeError(f"the TASK schema of the corpus of {worktree.project.name} declares no {undeclared}")


def _require_promotion_fields(runtime: Runtime, worktree: TaskWorktree) -> None:
    schema = read_awawa_document(runtime.run_process, worktree.path, ("show", "TASK"))
    declared = {field["atoms"][0]: field["atoms"][1] for field in schema["fields"] if field["name"] == "FIELD"}
    if IMPLEMENTED not in declared["STATUS"].split(TYPE_SEPARATOR):
        raise _refuse_undeclared(worktree, f"STATUS {IMPLEMENTED}")
    if DELIVERED_BY not in declared:
        raise _refuse_undeclared(worktree, DELIVERED_BY)


def _promote(text: str, task: str, pr: int) -> str:
    lines = text.splitlines(keepends=True)
    block = locate_entity_block(lines, "TASK", task)
    status = next(index for index in block if lines[index].startswith(STATUS_LINE))
    lines[status : status + 1] = [f"{STATUS_LINE}{IMPLEMENTED}\n", f"\t{DELIVERED_BY} {pr}\n"]
    return "".join(lines)


def promote_task(runtime: Runtime, demand: TaskPromotionDemand) -> dict:
    worktree = locate_task_worktree(runtime, demand.path, demand.task)
    pr = demand.pr if demand.pr is not None else _read_recorded_pull_request(runtime, worktree)
    _require_promotion_fields(runtime, worktree)
    shown = read_awawa_document(runtime.run_process, worktree.path, ("show", f"@TASK.{worktree.task}"))
    file_name = str(Path(shown["file"]).relative_to(worktree.path))
    change_corpus_file(
        runtime.run_process,
        CorpusChange(
            repository=worktree.path,
            lock=locate_corpus_lock(runtime.paths.lock_directory, worktree.path),
            file_names=(file_name,),
            describe_message=lambda: f"docs(corpus): mark @TASK.{worktree.task} implemented, delivered by #{pr}",
            rewrite=lambda texts: (_promote(texts[0], worktree.task, pr),),
        ),
    )
    branch = read_current_branch(runtime.run_process, worktree.path)
    push_branch(
        runtime.run_process, BranchPush(repository=worktree.path, branch=branch, environment=demand.environment)
    )
    commit = resolve_commit(runtime.run_process, worktree.path, HEAD)
    append_event(
        runtime.paths,
        runtime.now,
        TaskPromoted(project=worktree.project.name, task=worktree.task, pr=pr, commit=commit),
    )
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "project": worktree.project.name,
        "task": worktree.task,
        "pr": pr,
        "commit": commit,
    }
