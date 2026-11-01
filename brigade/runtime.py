import functools
import sys
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from brigade.ledger.read_ledger import LedgerReading, read_ledger
from brigade.system.paths import Paths, build_paths
from brigade.system.poll_until_signalled import poll_until_signalled
from brigade.system.process_trace import ProcessTrace
from brigade.system.render_trace import render_trace
from brigade.system.resolve_plugin import PluginSources, resolve_plugin
from brigade.system.run_process import ProcessRecord, ProcessRequest, run_process
from brigade.system.spawn_process import SpawnRequest, spawn_process
from brigade.system.trail_writer import TrailWriter
from brigade.tick.read_live_blockers import read_live_blockers


@dataclass(frozen=True)
class Invocation:
    command: str
    verbose: bool


@dataclass(frozen=True)
class Runtime:
    run_process: Callable[[ProcessRequest], ProcessRecord]
    spawn_process: Callable[[SpawnRequest], object]
    paths: Paths
    now: datetime
    read_clock: Callable[[], datetime]
    read_monotonic: Callable[[], float]
    entry_point: Path
    trail: TrailWriter
    resolve_plugin: Callable[..., object]
    poll_until_signalled: Callable[[Callable[[], bool], float], bool]
    read_ledger: Callable[[Path], LedgerReading]
    read_live_blockers: Callable[[Callable[[ProcessRequest], ProcessRecord], Path, str], tuple[str, ...]]


def _report_nothing(trace: ProcessTrace) -> None:
    pass


def _choose_report(invocation: Invocation) -> Callable[[ProcessTrace], None]:
    if not invocation.verbose:
        return _report_nothing
    return lambda trace: sys.stderr.write(f"brigade {invocation.command}: {render_trace(trace)}\n")


def build_runtime(invocation: Invocation, environment: Mapping[str, str]) -> Runtime:
    trail = TrailWriter(_choose_report(invocation))
    paths = build_paths(environment)
    run_recorded_process = functools.partial(run_process, record_trace=trail.append, environment=environment)
    sources = PluginSources(executable_search_path=paths.executable_search_path, run_process=run_recorded_process)
    return Runtime(
        run_process=run_recorded_process,
        spawn_process=functools.partial(spawn_process, record_trace=trail.append, environment=environment),
        paths=paths,
        now=datetime.now(UTC),
        read_clock=functools.partial(datetime.now, UTC),
        read_monotonic=time.monotonic,
        entry_point=Path(sys.argv[0]).absolute(),
        trail=trail,
        resolve_plugin=functools.partial(resolve_plugin, sources=sources),
        poll_until_signalled=poll_until_signalled,
        read_ledger=read_ledger,
        read_live_blockers=read_live_blockers,
    )
