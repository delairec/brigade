from pathlib import Path

CHECKS_DIRECTORY = "checks"
RECORD_SUFFIX = ".json"


def locate_check_record(state_root: Path, project: str, task: str) -> Path:
    return state_root / CHECKS_DIRECTORY / project / f"{task}{RECORD_SUFFIX}"
