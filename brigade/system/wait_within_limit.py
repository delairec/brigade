import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass

from brigade.system.stop_process_group import stop_process_group


@dataclass(frozen=True)
class WallLimit:
    limit_s: float
    grace_before_kill_s: float
    poll_s: float


def wait_within_limit(process: subprocess.Popen, limit: WallLimit, on_poll: Callable[[], None]) -> int | None:
    deadline = time.monotonic() + limit.limit_s
    try:
        while (remaining_s := deadline - time.monotonic()) > 0:
            try:
                return process.wait(timeout=min(limit.poll_s, remaining_s))
            except subprocess.TimeoutExpired:
                on_poll()
    except BaseException:
        stop_process_group(process, limit.grace_before_kill_s)
        raise
    stop_process_group(process, limit.grace_before_kill_s)
    return None
