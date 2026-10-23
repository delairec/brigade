import fcntl
from pathlib import Path


def try_lock(path: Path) -> bool:
    with path.open("a") as other_holder:
        try:
            fcntl.flock(other_holder, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        return True
