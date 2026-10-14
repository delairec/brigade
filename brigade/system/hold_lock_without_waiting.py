import fcntl
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TextIO

from brigade.errors import CannotWrite


def _open_lock_file(path: Path) -> TextIO:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        return path.open("a", encoding="utf-8")
    except OSError as error:
        raise CannotWrite(error.filename or path, error) from error


@contextmanager
def hold_lock_without_waiting(path: Path) -> Iterator[bool]:
    with _open_lock_file(path) as lock_file:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            lock_file.truncate(0)
            lock_file.write(f"{os.getpid()}\n")
            lock_file.flush()
        except BlockingIOError:
            yield False
            return
        except OSError as error:
            raise CannotWrite(path, error) from error
        try:
            yield True
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
