from dataclasses import dataclass
from typing import Callable

from brigade.system.run_process import ProcessRecord, ProcessRequest, run_process


@dataclass(frozen=True)
class Runtime:
    run_process: Callable[[ProcessRequest], ProcessRecord]


def build_runtime() -> Runtime:
    return Runtime(run_process=run_process)
