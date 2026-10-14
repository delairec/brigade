import os
import tempfile
from pathlib import Path

from brigade.errors import CannotWrite


def _fill_and_replace(descriptor: int, temporary_name: str, path: Path, content: str) -> None:
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as temporary_file:
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        Path(temporary_name).replace(path)
    except OSError as error:
        raise CannotWrite(path, error) from error


def write_text_atomically(path: Path, content: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise CannotWrite(error.filename or path.parent, error) from error
    try:
        descriptor, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    except OSError as error:
        raise CannotWrite(path, error) from error
    try:
        _fill_and_replace(descriptor, temporary_name, path, content)
    except BaseException:
        Path(temporary_name).unlink(missing_ok=True)
        raise
