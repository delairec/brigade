from pathlib import Path

from brigade.system.is_executable import is_executable


def list_executables(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(path for path in directory.iterdir() if is_executable(path))
