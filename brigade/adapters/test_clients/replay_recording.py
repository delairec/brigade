import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from brigade.system.append_line import append_line

HOLD_POLL_S = 0.05
SOFT_LIMIT_POLL_S = 0.1


@dataclass(frozen=True)
class ReplayClock:
    read_epoch: Callable[[], float]
    sleep: Callable[[float], None]


def replay_recording(arguments: list[str], clock: ReplayClock, output: TextIO) -> None:
    hold, progress, progress_file, recording, interval, soft_limit = arguments
    while hold and Path(hold).exists():
        clock.sleep(HOLD_POLL_S)
    while clock.read_epoch() < int(soft_limit):
        clock.sleep(SOFT_LIMIT_POLL_S)
    if progress:
        append_line(Path(progress_file), progress)
    for line in Path(recording).read_text(encoding="utf-8").splitlines():
        output.write(f"{line}\n")
        output.flush()
        clock.sleep(float(interval))


if __name__ == "__main__":
    replay_recording(sys.argv[1:], ReplayClock(read_epoch=time.time, sleep=time.sleep), sys.stdout)
