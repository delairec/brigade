import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from brigade.system.paths import Paths, build_paths
from brigade.system.run_process import ProcessRecord, ProcessRequest, run_process


@dataclass(frozen=True)
class Runtime:
    run_process: Callable[[ProcessRequest], ProcessRecord]
    paths: Paths
    now: datetime
    entry_point: Path


def build_runtime() -> Runtime:
    return Runtime(
        run_process=run_process,
        paths=build_paths(),
        now=datetime.now(timezone.utc),
        entry_point=Path(sys.argv[0]).absolute(),
    )
