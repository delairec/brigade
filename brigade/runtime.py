import functools
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from brigade.system.paths import Paths, build_paths
from brigade.system.process_trace import ProcessTrace
from brigade.system.render_trace import render_trace
from brigade.system.resolve_plugin import PluginSources, resolve_plugin
from brigade.system.run_process import ProcessRecord, ProcessRequest, run_process
from brigade.system.spawn_process import SpawnRequest, spawn_process
from brigade.system.trail_writer import TrailWriter


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
    entry_point: Path
    trail: TrailWriter
    resolve_plugin: Callable[[str, str], object]


def _report_nothing(trace: ProcessTrace) -> None:
    pass


def _choose_report(invocation: Invocation) -> Callable[[ProcessTrace], None]:
    if not invocation.verbose:
        return _report_nothing
    return lambda trace: sys.stderr.write(f"brigade {invocation.command}: {render_trace(trace)}\n")


def build_runtime(invocation: Invocation) -> Runtime:
    trail = TrailWriter(_choose_report(invocation))
    paths = build_paths()
    run_recorded_process = functools.partial(run_process, record_trace=trail.append)
    sources = PluginSources(executable_search_path=paths.executable_search_path, run_process=run_recorded_process)
    return Runtime(
        run_process=run_recorded_process,
        spawn_process=functools.partial(spawn_process, record_trace=trail.append),
        paths=paths,
        now=datetime.now(UTC),
        entry_point=Path(sys.argv[0]).absolute(),
        trail=trail,
        resolve_plugin=functools.partial(resolve_plugin, sources=sources),
    )
