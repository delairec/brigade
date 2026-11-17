from collections.abc import Callable
from pathlib import Path

from brigade.corpus.check_corpus import CORPUS_CHECKS
from brigade.corpus.run_awawa import run_awawa
from brigade.system.run_process import ProcessRecord, ProcessRequest
from brigade.verify.describe_command_record import describe_command_record
from brigade.verify.judge_findings import judge_findings

NAME = "corpus"


def _describe_failure(record: ProcessRecord) -> list[str]:
    output = (record.stdout + record.stderr).splitlines()
    return [f"{' '.join(record.argv)} exited {record.exit_code}", *output]


def check_corpus_at_head(run_process: Callable[[ProcessRequest], ProcessRecord], head_tree: Path) -> dict:
    records = [run_awawa(run_process, head_tree, arguments) for arguments in CORPUS_CHECKS]
    findings = [finding for record in records if record.exit_code != 0 for finding in _describe_failure(record)]
    return {
        **judge_findings(NAME, findings),
        "commands": [describe_command_record(" ".join(record.argv), record) for record in records],
    }
