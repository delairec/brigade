from collections.abc import Callable
from pathlib import Path

from brigade.corpus.run_awawa import SUCCESS, run_awawa
from brigade.system.run_process import ProcessRecord, ProcessRequest

PROBE_DIRECTORY = Path("/")


def read_awawa_version(run_process: Callable[[ProcessRequest], ProcessRecord]) -> str:
    record = run_awawa(run_process, PROBE_DIRECTORY, ("--version",), SUCCESS)
    return record.stdout.strip().removeprefix("awawa ")
