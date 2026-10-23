import functools
import os
from collections.abc import Callable

from brigade.system.process_trace import ProcessTrace
from brigade.system.run_process import ProcessRecord, ProcessRequest, run_process


def _keep_no_trace(trace: ProcessTrace) -> None:
    pass


def create_process_runner(search_path: str) -> Callable[[ProcessRequest], ProcessRecord]:
    return functools.partial(run_process, record_trace=_keep_no_trace, environment={**os.environ, "PATH": search_path})
