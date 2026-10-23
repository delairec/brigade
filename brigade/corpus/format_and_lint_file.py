from collections.abc import Callable
from pathlib import Path

from brigade.corpus.lint_corpus import CLEAN, CLEAN_OR_FINDINGS, LintReport
from brigade.corpus.run_awawa import run_awawa
from brigade.system.run_process import ProcessRecord, ProcessRequest


def format_and_lint_file(run_process: Callable[[ProcessRequest], ProcessRecord], file: Path) -> LintReport:
    run_awawa(run_process, file.parent, ("fmt", str(file)))
    record = run_awawa(run_process, file.parent, ("lint", "--strict", str(file)), CLEAN_OR_FINDINGS)
    return LintReport(clean=record.exit_code == CLEAN, output=(record.stdout + record.stderr).strip())
