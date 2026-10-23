from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from brigade.errors import CannotWrite


@contextmanager
def refuse_failed_write(path: Path) -> Iterator[None]:
    try:
        yield
    except OSError as error:
        raise CannotWrite(error.filename or path, error) from error
