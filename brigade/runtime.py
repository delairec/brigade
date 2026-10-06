import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

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
        now=datetime.now(UTC),
        entry_point=Path(sys.argv[0]).absolute(),
    )
