from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.run_awawa import run_awawa
from brigade.system.run_process import ProcessRecord, ProcessRequest

CLEAN_OR_FINDINGS = (0, 1)
CLEAN = 0


@dataclass(frozen=True)
class LintReport:
    clean: bool
    output: str


def lint_corpus(run_process: Callable[[ProcessRequest], ProcessRecord], root: Path) -> LintReport:
    record = run_awawa(run_process, root, ("lint", "--strict", str(root)), CLEAN_OR_FINDINGS)
    return LintReport(clean=record.exit_code == CLEAN, output=(record.stdout + record.stderr).strip())
