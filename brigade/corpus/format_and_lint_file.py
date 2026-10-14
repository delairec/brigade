from collections.abc import Callable
from pathlib import Path

from brigade.corpus.lint_corpus import AWAWA_TIMEOUT_S, CLEAN, CLEAN_OR_FINDINGS, LintReport
from brigade.system.run_process import EVERY_EXIT_CODE, ProcessRecord, ProcessRequest


def format_and_lint_file(run_process: Callable[[ProcessRequest], ProcessRecord], file: Path) -> LintReport:
    directory = str(file.parent)
    run_process(
        ProcessRequest(
            argv=("awawa", "fmt", str(file)),
            cwd=directory,
            timeout_s=AWAWA_TIMEOUT_S,
            acceptable_exit_codes=EVERY_EXIT_CODE,
        )
    )
    record = run_process(
        ProcessRequest(
            argv=("awawa", "lint", "--strict", str(file)),
            cwd=directory,
            timeout_s=AWAWA_TIMEOUT_S,
            acceptable_exit_codes=CLEAN_OR_FINDINGS,
        )
    )
    return LintReport(clean=record.exit_code == CLEAN, output=(record.stdout + record.stderr).strip())
