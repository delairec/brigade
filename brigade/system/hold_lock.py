import fcntl
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


@contextmanager
def hold_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        try:
            lock_file.truncate(0)
            lock_file.write(f"{os.getpid()}\n")
            lock_file.flush()
            yield
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
