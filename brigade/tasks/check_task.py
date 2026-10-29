from brigade.corpus.check_corpus import check_corpus
from brigade.errors import BrigadeError
from brigade.git.fetch_branches import REMOTE
from brigade.git.find_merge_base import find_merge_base
from brigade.git.list_added_lines import list_added_lines
from brigade.git.list_changed_files import list_changed_files
from brigade.git.resolve_commit import resolve_commit
from brigade.registry.is_on_github import is_on_github
from brigade.runtime import Runtime
from brigade.system.run_process import EVERY_EXIT_CODE, ProcessRecord, ProcessRequest
from brigade.system.split_command import split_command
from brigade.system.write_json_atomically import write_json_atomically
from brigade.system.write_text_atomically import write_text_atomically
from brigade.tasks.locate_check_record import locate_check_record
from brigade.tasks.locate_task_worktree import TaskWorktree
from brigade.verify.check_privacy import check_privacy
from brigade.verify.judge_findings import PASSED
from brigade.verify.read_privacy_patterns import read_privacy_patterns

DOCUMENT_SCHEMA_VERSION = 1
ACCEPTANCE_FIELD = "ACCEPTANCE"
CHECK_TIMEOUT_S = 1800.0
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


def _run_acceptance_line(
    runtime: Runtime, worktree: TaskWorktree, command: tuple[str, tuple[str, ...]]
) -> tuple[str, ProcessRecord]:
    line, argv = command
    record = runtime.run_process(
        ProcessRequest(
            argv=argv, cwd=str(worktree.path), timeout_s=CHECK_TIMEOUT_S, acceptable_exit_codes=EVERY_EXIT_CODE
        )
    )
    return line, record


def _record_check(runtime: Runtime, rank: int, check: tuple[str, ProcessRecord]) -> dict:
    command, record = check
    output = f"{record.stdout}{record.stderr}"
    _write_output(runtime, rank, output)
    return _describe_check(command, record, output)


def _require_worktree_at_head(runtime: Runtime, worktree: TaskWorktree) -> None:
    changed = list_changed_files(runtime.run_process, worktree.path)
    if changed:
        raise BrigadeError(
            f"the worktree of @TASK.{worktree.task} holds changes HEAD does not: {', '.join(changed)};"
            " commit them, then run brigade task check"
        )


def _locate_start(worktree: TaskWorktree) -> str:
    if is_on_github(worktree.project):
        return f"{REMOTE}/{worktree.wave_branch}"
    return worktree.wave_branch


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
    acceptance = tuple(field.value for field in worktree.project.fields if field.name == ACCEPTANCE_FIELD)
    commands = tuple((line, split_command(line)) for line in acceptance)
    head = resolve_commit(runtime.run_process, worktree.path, HEAD)
    checks = (
        *(_run_acceptance_line(runtime, worktree, command) for command in commands),
        *((check.command, check.record) for check in check_corpus(runtime.run_process, worktree.path)),
    )
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
