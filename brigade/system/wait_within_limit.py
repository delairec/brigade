import os
import signal
import subprocess
from typing import Optional

GRACE_BEFORE_KILL_S = 30.0


def _signal_group(process: subprocess.Popen, signal_number: int) -> None:
    try:
        os.killpg(process.pid, signal_number)
    except ProcessLookupError:
        pass


def wait_within_limit(process: subprocess.Popen, limit_s: float) -> Optional[int]:
    try:
        return process.wait(timeout=limit_s)
    except subprocess.TimeoutExpired:
        pass
    _signal_group(process, signal.SIGTERM)
    try:
        process.wait(timeout=GRACE_BEFORE_KILL_S)
    except subprocess.TimeoutExpired:
        _signal_group(process, signal.SIGKILL)
        process.wait()
    return None
