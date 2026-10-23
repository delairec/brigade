import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from brigade.errors import CannotWrite

HIDDEN_PREFIX = "."


@contextmanager
def stage_directory(tree: Path) -> Iterator[Path]:
    try:
        staging = Path(tempfile.mkdtemp(prefix=HIDDEN_PREFIX, dir=tree.parent))
    except OSError as error:
        raise CannotWrite(tree, error) from error
    try:
        yield staging
    except OSError as error:
        raise CannotWrite(tree, error) from error
    finally:
        shutil.rmtree(staging, ignore_errors=True)
