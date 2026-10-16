from pathlib import Path

SETUP_LOG_SUFFIX = ".log"


def locate_setup_log(setup_directory: Path, project: str, task: str) -> Path:
    return setup_directory / project / f"{task}{SETUP_LOG_SUFFIX}"
