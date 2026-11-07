from pathlib import Path

COMMIT_CHECKS_DIRECTORY = "commit-checks"
RECORD_SUFFIX = ".json"


def locate_commit_check_record(state_root: Path, project: str, commit: str) -> Path:
    return state_root / COMMIT_CHECKS_DIRECTORY / project / f"{commit}{RECORD_SUFFIX}"
