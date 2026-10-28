from collections.abc import Callable

from brigade.errors import ToolNotFound
from brigade.system.run_process import ProcessRecord, ProcessRequest

PROBE_DIRECTORY = "/"
PROBE_TIMEOUT_S = 10.0


def find_awawa_web(run_process: Callable[[ProcessRequest], ProcessRecord]) -> bool:
    try:
        run_process(ProcessRequest(argv=("awawa-web", "--help"), cwd=PROBE_DIRECTORY, timeout_s=PROBE_TIMEOUT_S))
    except ToolNotFound:
        return False
    return True
