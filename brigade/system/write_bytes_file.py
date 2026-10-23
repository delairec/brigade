from pathlib import Path

from brigade.errors import CannotWrite


def write_bytes_file(path: Path, content: bytes) -> None:
    try:
        path.write_bytes(content)
    except OSError as error:
        raise CannotWrite(error.filename or path, error) from error
