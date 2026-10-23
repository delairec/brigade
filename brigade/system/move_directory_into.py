from pathlib import Path

from brigade.errors import CannotWrite


def move_directory_into(directory: Path, destination: Path) -> Path:
    try:
        destination.mkdir(parents=True, exist_ok=True)
        return directory.rename(destination / directory.name)
    except OSError as error:
        raise CannotWrite(destination, error) from error
