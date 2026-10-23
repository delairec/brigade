import shutil
from pathlib import Path

from brigade.errors import CannotWrite


def delete_path(path: Path) -> None:
    try:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    except OSError as error:
        raise CannotWrite(path, error) from error
