from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.check_corpus import check_corpus
from brigade.corpus.read_entities import Entity
from brigade.registry.read_corpus_workspace import read_corpus_workspace
from brigade.system.run_process import EVERY_EXIT_CODE, ProcessRecord, ProcessRequest
from brigade.system.split_command import split_command

ACCEPTANCE_FIELD = "ACCEPTANCE"
CHECK_TIMEOUT_S = 1800.0


@dataclass(frozen=True)
class ProjectCheck:
    command: str
    record: ProcessRecord


def _run_acceptance_line(
    run_process: Callable[[ProcessRequest], ProcessRecord], root: Path, line: str, argv: tuple[str, ...]
) -> ProjectCheck:
    record = run_process(
        ProcessRequest(argv=argv, cwd=str(root), timeout_s=CHECK_TIMEOUT_S, acceptable_exit_codes=EVERY_EXIT_CODE)
    )
    return ProjectCheck(command=line, record=record)


def run_project_checks(
    run_process: Callable[[ProcessRequest], ProcessRecord], project: Entity, root: Path
) -> tuple[ProjectCheck, ...]:
    acceptance = tuple(field.value for field in project.fields if field.name == ACCEPTANCE_FIELD)
    corpus_root = root / read_corpus_workspace(project)
    commands = tuple((line, split_command(line)) for line in acceptance)
    return (
        *(_run_acceptance_line(run_process, root, line, argv) for line, argv in commands),
        *(ProjectCheck(command=check.command, record=check.record) for check in check_corpus(run_process, corpus_root)),
    )
