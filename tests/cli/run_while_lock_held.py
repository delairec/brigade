import fcntl
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from tests.process_launcher import ProcessLauncher

HOLDER_PID = 4242


@contextmanager
def run_while_lock_held(argv: list, environment: dict, lock_file: Path) -> Iterator[str]:
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    with lock_file.open("a") as held_lock:
        fcntl.flock(held_lock, fcntl.LOCK_EX)
        held_lock.truncate(0)
        held_lock.write(f"{HOLDER_PID}\n")
        held_lock.flush()
        waiting = ProcessLauncher.start(
            argv, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, env=environment
        )
        try:
            yield waiting.stderr.readline()
        finally:
            fcntl.flock(held_lock, fcntl.LOCK_UN)
            waiting.communicate()
