from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.corpus.run_awawa import run_awawa
from brigade.system.run_process import ProcessRecord, ProcessRequest

CORPUS_CHECKS = (("fmt", "--check", "."), ("lint", "--strict", "."))


@dataclass(frozen=True)
class CorpusCheck:
    command: str
    record: ProcessRecord


def check_corpus(run_process: Callable[[ProcessRequest], ProcessRecord], root: Path) -> tuple[CorpusCheck, ...]:
    return tuple(
        CorpusCheck(command=" ".join(("awawa", *arguments)), record=run_awawa(run_process, root, arguments))
        for arguments in CORPUS_CHECKS
    )
