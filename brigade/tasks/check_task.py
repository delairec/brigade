from brigade.errors import BrigadeError
from brigade.git.fetch_branches import REMOTE
from brigade.git.find_merge_base import find_merge_base
from brigade.git.list_added_lines import list_added_lines
from brigade.git.list_changed_files import list_changed_files
from brigade.git.resolve_commit import resolve_commit
from brigade.registry.is_on_a_forge import is_on_a_forge
from brigade.runtime import Runtime
from brigade.system.run_process import ProcessRecord
from brigade.system.write_json_atomically import write_json_atomically
from brigade.system.write_text_atomically import write_text_atomically
from brigade.tasks.locate_check_record import locate_check_record
from brigade.tasks.locate_task_worktree import TaskWorktree
from brigade.tasks.run_project_checks import ProjectCheck, run_project_checks
from brigade.verify.check_privacy import check_privacy
from brigade.verify.judge_findings import PASSED
from brigade.verify.read_privacy_patterns import read_privacy_patterns

DOCUMENT_SCHEMA_VERSION = 1
TAIL_LINES = 20
CHECK_DIRECTORY = "check"
OUTPUT_SUFFIX = ".log"
HEAD = "HEAD"
MS_PER_S = 1000


def _write_output(runtime: Runtime, rank: int, output: str) -> None:
    if runtime.paths.run_directory is None:
        return
    write_text_atomically(runtime.paths.run_directory / CHECK_DIRECTORY / f"{rank}{OUTPUT_SUFFIX}", output)


def _describe_check(command: str, record: ProcessRecord, output: str) -> dict:
    passed = record.exit_code == 0
    return {
        "command": command,
        "passed": passed,
        "duration_ms": record.duration_ms,
        "tail": [] if passed else output.splitlines()[-TAIL_LINES:],
    }


def _record_check(runtime: Runtime, rank: int, check: ProjectCheck) -> dict:
    output = f"{check.record.stdout}{check.record.stderr}"
    _write_output(runtime, rank, output)
    return _describe_check(check.command, check.record, output)


def _require_worktree_at_head(runtime: Runtime, worktree: TaskWorktree) -> None:
    changed = list_changed_files(runtime.run_process, worktree.path)
    if changed:
        raise BrigadeError(
            f"the worktree of @TASK.{worktree.task} holds changes HEAD does not: {', '.join(changed)};"
            " commit them, then run brigade task check"
        )


def _locate_start(worktree: TaskWorktree) -> str:
    if is_on_a_forge(worktree.project):
        return f"{REMOTE}/{worktree.base}"
    return worktree.base


def _check_privacy_of_the_task(runtime: Runtime, worktree: TaskWorktree, head: str) -> dict:
    started = runtime.read_monotonic()
    base = find_merge_base(runtime.run_process, worktree.path, _locate_start(worktree), head)
    added_lines = list_added_lines(runtime.run_process, worktree.path, base, head)
    judgment = check_privacy(read_privacy_patterns(worktree.project), added_lines)
    return {
        "command": judgment["name"],
        "passed": judgment["verdict"] == PASSED,
        "duration_ms": round((runtime.read_monotonic() - started) * MS_PER_S),
        "tail": judgment["findings"],
    }


def check_task(runtime: Runtime, worktree: TaskWorktree) -> dict:
    _require_worktree_at_head(runtime, worktree)
    checks = run_project_checks(runtime.run_process, worktree.project, worktree.path)
    head = resolve_commit(runtime.run_process, worktree.path, HEAD)
    document = {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "project": worktree.project.name,
        "task": worktree.task,
        "head": head,
        "checks": [
            *(_record_check(runtime, rank, check) for rank, check in enumerate(checks, start=1)),
            _check_privacy_of_the_task(runtime, worktree, head),
        ],
    }
    write_json_atomically(locate_check_record(runtime.paths.state_root, worktree.project.name, worktree.task), document)
    return document
