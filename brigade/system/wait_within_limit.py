import os
import signal
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class WallLimit:
    limit_s: float
    grace_before_kill_s: float
    poll_s: float


def _signal_group(process: subprocess.Popen, signal_number: int) -> None:
    try:
        os.killpg(process.pid, signal_number)
    except ProcessLookupError:
        pass


def wait_within_limit(process: subprocess.Popen, limit: WallLimit, on_poll: Callable[[], None]) -> int | None:
    deadline = time.monotonic() + limit.limit_s
    while (remaining_s := deadline - time.monotonic()) > 0:
        try:
            return process.wait(timeout=min(limit.poll_s, remaining_s))
        except subprocess.TimeoutExpired:
            on_poll()
    _signal_group(process, signal.SIGTERM)
    try:
        process.wait(timeout=limit.grace_before_kill_s)
    except subprocess.TimeoutExpired:
        _signal_group(process, signal.SIGKILL)
        process.wait()
    return None
