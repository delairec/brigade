import shutil
import uuid
from pathlib import Path

from brigade.errors import CannotWrite

HIDDEN_PREFIX = "."


def remove_directory(directory: Path) -> None:
    doomed = directory.parent / f"{HIDDEN_PREFIX}{directory.name}.{uuid.uuid4().hex}"
    try:
        directory.rename(doomed)
    except OSError as error:
        raise CannotWrite(directory, error) from error
    shutil.rmtree(doomed, ignore_errors=True)
