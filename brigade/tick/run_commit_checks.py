import shlex
from pathlib import Path

from brigade.corpus.read_entities import Entity
from brigade.recipes.locate_recipes import locate_recipes
from brigade.recipes.read_project_commands import read_project_commands
from brigade.runtime import Runtime
from brigade.system.run_process import EVERY_EXIT_CODE, ProcessRequest
from brigade.system.write_json_atomically import write_json_atomically
from brigade.tasks.run_project_checks import run_project_checks
from brigade.tick.commit_checks import CommandResult, CommitChecks
from brigade.tick.locate_commit_check_record import locate_commit_check_record

SETUP_RECIPE = "setup"
SETUP_TIMEOUT_S = 1800.0
DOCUMENT_SCHEMA_VERSION = 1


def _run_setup_step(runtime: Runtime, worktree: Path, argv: tuple[str, ...]) -> CommandResult:
    record = runtime.run_process(
        ProcessRequest(
            argv=argv,
            cwd=str(worktree),
            timeout_s=SETUP_TIMEOUT_S,
            acceptable_exit_codes=EVERY_EXIT_CODE,
        )
    )
    return CommandResult(command=shlex.join(argv), exit_code=record.exit_code)


def _describe_record(checks: CommitChecks) -> dict:
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "project": checks.project,
        "commit": checks.commit,
        "checks": [{"command": result.command, "exit_code": result.exit_code} for result in checks.results],
    }


def run_commit_checks(runtime: Runtime, project: Entity, worktree: Path, commit: str) -> CommitChecks:
    setup = read_project_commands(locate_recipes(worktree, project, runtime.paths), SETUP_RECIPE, runtime.run_process)
    results = (
        *(_run_setup_step(runtime, worktree, argv) for argv in setup),
        *(
            CommandResult(command=check.command, exit_code=check.record.exit_code)
            for check in run_project_checks(runtime, project, worktree)
        ),
    )
    checks = CommitChecks(project=project.name, commit=commit, results=results)
    write_json_atomically(
        locate_commit_check_record(runtime.paths.state_root, project.name, commit), _describe_record(checks)
    )
    return checks
