import contextlib
import os
import signal
import subprocess


def _signal_group(process: subprocess.Popen, signal_number: int) -> None:
    with contextlib.suppress(ProcessLookupError):
        os.killpg(process.pid, signal_number)


def stop_process_group(process: subprocess.Popen, grace_before_kill_s: float) -> None:
    _signal_group(process, signal.SIGTERM)
    try:
        process.wait(timeout=grace_before_kill_s)
    except subprocess.TimeoutExpired:
        _signal_group(process, signal.SIGKILL)
        process.wait()
