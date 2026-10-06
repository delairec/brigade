from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.system.run_process import ProcessRecord, ProcessRequest

AWAWA_TIMEOUT_S = 30.0
CLEAN_OR_FINDINGS = (0, 1)
CLEAN = 0


@dataclass(frozen=True)
class LintReport:
    clean: bool
    output: str


def lint_corpus(run_process: Callable[[ProcessRequest], ProcessRecord], root: Path) -> LintReport:
    record = run_process(
        ProcessRequest(
            argv=("awawa", "lint", "--strict", str(root)),
            cwd=str(root),
            timeout_s=AWAWA_TIMEOUT_S,
            acceptable_exit_codes=CLEAN_OR_FINDINGS,
        )
    )
    return LintReport(clean=record.exit_code == CLEAN, output=(record.stdout + record.stderr).strip())
