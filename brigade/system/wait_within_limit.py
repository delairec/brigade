import os
import signal
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class WallLimit:
    limit_s: float
    grace_before_kill_s: float


def _signal_group(process: subprocess.Popen, signal_number: int) -> None:
    try:
        os.killpg(process.pid, signal_number)
    except ProcessLookupError:
        pass


def wait_within_limit(process: subprocess.Popen, limit: WallLimit) -> int | None:
    try:
        return process.wait(timeout=limit.limit_s)
    except subprocess.TimeoutExpired:
        pass
    _signal_group(process, signal.SIGTERM)
    try:
        process.wait(timeout=limit.grace_before_kill_s)
    except subprocess.TimeoutExpired:
        _signal_group(process, signal.SIGKILL)
        process.wait()
    return None
