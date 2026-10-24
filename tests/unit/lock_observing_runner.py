import fcntl
from collections.abc import Callable
from pathlib import Path

from brigade.system.run_process import ProcessRecord, ProcessRequest


def _is_free(lock: Path) -> bool:
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("a", encoding="utf-8") as probe:
        try:
            fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        return True


class LockObservingRunner:
    def __init__(self, run_process: Callable[[ProcessRequest], ProcessRecord], lock: Path, argv: tuple[str, ...]):
        self._run_process = run_process
        self._lock = lock
        self._argv = argv
        self.lock_free_at_the_command: list[bool] = []

    def __call__(self, request: ProcessRequest) -> ProcessRecord:
        if request.argv == self._argv:
            self.lock_free_at_the_command.append(_is_free(self._lock))
        return self._run_process(request)
