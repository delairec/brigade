import fcntl
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from brigade.errors import CannotWrite


@contextmanager
def hold_lock(path: Path) -> Iterator[None]:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        lock_file = open(path, "a", encoding="utf-8")
    except OSError as error:
        raise CannotWrite(error.filename or path, error) from error
    with lock_file:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            lock_file.truncate(0)
            lock_file.write(f"{os.getpid()}\n")
            lock_file.flush()
        except OSError as error:
            raise CannotWrite(path, error) from error
        try:
            yield
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
