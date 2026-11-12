from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from brigade.system.run_process import EVERY_EXIT_CODE, ProcessRecord, ProcessRequest
from brigade.system.split_command import split_command
from brigade.verify.judge_findings import judge_findings

NAME = "acceptance"
ACCEPTANCE_TIMEOUT_S = 1800.0


@dataclass(frozen=True)
class AcceptanceFacts:
    head_tree: Path
    commands: tuple[str, ...]


def _run_command(
    run_process: Callable[[ProcessRequest], ProcessRecord], head_tree: Path, command: str
) -> ProcessRecord:
    return run_process(
        ProcessRequest(
            argv=split_command(command),
            cwd=str(head_tree),
            timeout_s=ACCEPTANCE_TIMEOUT_S,
            acceptable_exit_codes=EVERY_EXIT_CODE,
        )
    )


def _describe_failure(command: str, record: ProcessRecord) -> list[str]:
    return [f"{command} exited {record.exit_code}", *(record.stdout + record.stderr).splitlines()]


def check_acceptance(run_process: Callable[[ProcessRequest], ProcessRecord], facts: AcceptanceFacts) -> dict:
    records = [(command, _run_command(run_process, facts.head_tree, command)) for command in facts.commands]
    findings = [
        finding
        for command, record in records
        if record.exit_code != 0
        for finding in _describe_failure(command, record)
    ]
    return {
        **judge_findings(NAME, findings),
        "commands": [{"command": command, "exit_code": record.exit_code} for command, record in records],
    }
