import shlex
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.check_corpus import check_corpus
from brigade.corpus.read_entities import Entity
from brigade.recipes.locate_recipes import locate_recipes
from brigade.recipes.read_project_commands import read_project_commands
from brigade.registry.read_corpus_workspace import read_corpus_workspace
from brigade.runtime import Runtime
from brigade.system.run_process import EVERY_EXIT_CODE, ProcessRecord, ProcessRequest

ACCEPTANCE_RECIPE = "acceptance"
CHECK_TIMEOUT_S = 1800.0


@dataclass(frozen=True)
class ProjectCheck:
    command: str
    record: ProcessRecord


def _run_acceptance_step(
    run_process: Callable[[ProcessRequest], ProcessRecord], root: Path, argv: tuple[str, ...]
) -> ProjectCheck:
    record = run_process(
        ProcessRequest(argv=argv, cwd=str(root), timeout_s=CHECK_TIMEOUT_S, acceptable_exit_codes=EVERY_EXIT_CODE)
    )
    return ProjectCheck(command=shlex.join(argv), record=record)


def run_project_checks(runtime: Runtime, project: Entity, root: Path) -> tuple[ProjectCheck, ...]:
    run_process = runtime.run_process
    acceptance = read_project_commands(locate_recipes(root, project, runtime.paths), ACCEPTANCE_RECIPE, run_process)
    corpus_root = root / read_corpus_workspace(project)
    return (
        *(_run_acceptance_step(run_process, root, argv) for argv in acceptance),
        *(ProjectCheck(command=check.command, record=check.record) for check in check_corpus(run_process, corpus_root)),
    )
