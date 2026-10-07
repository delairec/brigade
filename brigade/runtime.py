import functools
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from brigade.system.paths import Paths, build_paths
from brigade.system.process_trace import ProcessTrace
from brigade.system.render_trace import render_trace
from brigade.system.run_process import ProcessRecord, ProcessRequest, run_process
from brigade.system.trail_writer import TrailWriter


@dataclass(frozen=True)
class Invocation:
    command: str
    verbose: bool


@dataclass(frozen=True)
class Runtime:
    run_process: Callable[[ProcessRequest], ProcessRecord]
    paths: Paths
    now: datetime
    entry_point: Path
    trail: TrailWriter


def _report_nothing(trace: ProcessTrace) -> None:
    pass


def _choose_report(invocation: Invocation) -> Callable[[ProcessTrace], None]:
    if not invocation.verbose:
        return _report_nothing
    return lambda trace: sys.stderr.write(f"brigade {invocation.command}: {render_trace(trace)}\n")


def build_runtime(invocation: Invocation) -> Runtime:
    trail = TrailWriter(_choose_report(invocation))
    return Runtime(
        run_process=functools.partial(run_process, record_trace=trail.append),
        paths=build_paths(),
        now=datetime.now(UTC),
        entry_point=Path(sys.argv[0]).absolute(),
        trail=trail,
    )
