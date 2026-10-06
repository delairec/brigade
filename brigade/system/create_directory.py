from pathlib import Path

from brigade.errors import CannotWrite


def create_directory(path: Path) -> None:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise CannotWrite(error.filename or path, error) from error
