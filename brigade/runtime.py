from dataclasses import dataclass
from typing import Callable

from brigade.system.paths import Paths, build_paths
from brigade.system.run_process import ProcessRecord, ProcessRequest, run_process


@dataclass(frozen=True)
class Runtime:
    run_process: Callable[[ProcessRequest], ProcessRecord]
    paths: Paths


def build_runtime() -> Runtime:
    return Runtime(run_process=run_process, paths=build_paths())
