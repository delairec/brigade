import fcntl
import os
import sys
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


def _wait_for_the_holder(lock_file: TextIO, path: Path) -> None:
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        holder = path.read_text(encoding="utf-8").strip()
        sys.stderr.write(f"brigade: waiting for the lock {path}, held by pid {holder}\n")
        sys.stderr.flush()
        fcntl.flock(lock_file, fcntl.LOCK_EX)


@contextmanager
def hold_lock(path: Path) -> Iterator[None]:
    with _open_lock_file(path) as lock_file:
        try:
            _wait_for_the_holder(lock_file, path)
            lock_file.truncate(0)
            lock_file.write(f"{os.getpid()}\n")
            lock_file.flush()
        except OSError as error:
            raise CannotWrite(path, error) from error
        try:
            yield
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
