import shlex
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.system.run_process import EVERY_EXIT_CODE, ProcessRecord, ProcessRequest
from brigade.verify.describe_command_record import describe_command_record
from brigade.verify.judge_findings import judge_findings

NAME = "acceptance"
ACCEPTANCE_TIMEOUT_S = 1800.0


@dataclass(frozen=True)
class AcceptanceFacts:
    head_tree: Path
    commands: tuple[tuple[str, ...], ...]


def _run_command(
    run_process: Callable[[ProcessRequest], ProcessRecord], head_tree: Path, argv: tuple[str, ...]
) -> ProcessRecord:
    return run_process(
        ProcessRequest(
            argv=argv,
            cwd=str(head_tree),
            timeout_s=ACCEPTANCE_TIMEOUT_S,
            acceptable_exit_codes=EVERY_EXIT_CODE,
        )
    )


def _describe_failure(command: str, record: ProcessRecord) -> list[str]:
    return [f"{command} exited {record.exit_code}", *(record.stdout + record.stderr).splitlines()]


def check_acceptance(run_process: Callable[[ProcessRequest], ProcessRecord], facts: AcceptanceFacts) -> dict:
    records = [(shlex.join(argv), _run_command(run_process, facts.head_tree, argv)) for argv in facts.commands]
    findings = [
        finding
        for command, record in records
        if record.exit_code != 0
        for finding in _describe_failure(command, record)
    ]
    return {
        **judge_findings(NAME, findings),
        "commands": [describe_command_record(command, record) for command, record in records],
    }
