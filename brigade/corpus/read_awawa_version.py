from collections.abc import Callable

from brigade.system.run_process import ProcessRecord, ProcessRequest

PROBE_DIRECTORY = "/"
PROBE_TIMEOUT_S = 10.0


def read_awawa_version(run_process: Callable[[ProcessRequest], ProcessRecord]) -> str:
    record = run_process(ProcessRequest(argv=("awawa", "--version"), cwd=PROBE_DIRECTORY, timeout_s=PROBE_TIMEOUT_S))
    return record.stdout.strip().removeprefix("awawa ")
