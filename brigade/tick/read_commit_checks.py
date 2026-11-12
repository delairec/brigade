import json
from pathlib import Path

from brigade.tick.commit_checks import CommandResult, CommitChecks
from brigade.tick.locate_commit_check_record import locate_commit_check_record


def read_commit_checks(state_root: Path, project: str, commit: str) -> CommitChecks | None:
    record = locate_commit_check_record(state_root, project, commit)
    if not record.exists():
        return None
    document = json.loads(record.read_text(encoding="utf-8"))
    return CommitChecks(
        project=document["project"],
        commit=document["commit"],
        results=tuple(
            CommandResult(command=check["command"], exit_code=check["exit_code"]) for check in document["checks"]
        ),
    )
