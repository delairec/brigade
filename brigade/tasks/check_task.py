from brigade.corpus.check_corpus import check_corpus
from brigade.git.resolve_commit import resolve_commit
from brigade.runtime import Runtime
from brigade.system.run_process import EVERY_EXIT_CODE, ProcessRecord, ProcessRequest
from brigade.system.split_command import split_command
from brigade.system.write_json_atomically import write_json_atomically
from brigade.system.write_text_atomically import write_text_atomically
from brigade.tasks.locate_check_record import locate_check_record
from brigade.tasks.locate_task_worktree import TaskWorktree

DOCUMENT_SCHEMA_VERSION = 1
ACCEPTANCE_FIELD = "ACCEPTANCE"
CHECK_TIMEOUT_S = 1800.0
TAIL_LINES = 20
CHECK_DIRECTORY = "check"
OUTPUT_SUFFIX = ".log"
HEAD = "HEAD"


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


def check_task(runtime: Runtime, worktree: TaskWorktree) -> dict:
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
        "checks": [_record_check(runtime, rank, check) for rank, check in enumerate(checks, start=1)],
    }
    write_json_atomically(locate_check_record(runtime.paths.state_root, worktree.project.name, worktree.task), document)
    return document
