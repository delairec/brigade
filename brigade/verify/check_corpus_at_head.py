from collections.abc import Callable
from pathlib import Path

from brigade.corpus.run_awawa import run_awawa
from brigade.system.run_process import ProcessRecord, ProcessRequest
from brigade.verify.judge_findings import judge_findings

NAME = "corpus"
CORPUS_CHECKS = (("fmt", "--check", "."), ("lint", "--strict", "."))


def _describe_failure(record: ProcessRecord) -> list[str]:
    output = (record.stdout + record.stderr).splitlines()
    return [f"{' '.join(record.argv)} exited {record.exit_code}", *output]


def check_corpus_at_head(run_process: Callable[[ProcessRequest], ProcessRecord], head_tree: Path) -> dict:
    records = [run_awawa(run_process, head_tree, arguments) for arguments in CORPUS_CHECKS]
    return judge_findings(
        NAME, [finding for record in records if record.exit_code != 0 for finding in _describe_failure(record)]
    )
