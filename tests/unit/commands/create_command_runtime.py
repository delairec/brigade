from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from brigade.runtime import Runtime
from brigade.system.paths import Paths
from brigade.system.trail_writer import TrailWriter

COMMAND_INSTANT = datetime(2026, 10, 19, 9, 0, tzinfo=UTC)


def _keep_no_trace(trace) -> None:
    pass


def _refuse_process(request):
    raise AssertionError(f"the command ran {request.argv}")


def _refuse_resolution(kind: str, name: str, **options):
    raise AssertionError(f"the command resolved the {kind} plugin {name}")


def create_command_runtime(
    root: Path,
    *,
    run_process: Callable = _refuse_process,
    resolve_plugin: Callable = _refuse_resolution,
    run_directory: Path | None = None,
) -> Runtime:
    return Runtime(
        run_process=run_process,
        spawn_process=_refuse_process,
        paths=Paths(
            config_root=root / "config" / "brigade",
            state_root=root / "state" / "brigade",
            cache_root=root / "cache" / "brigade",
            home=root / "home",
            executable_search_path=str(root / "bin"),
            run_directory=run_directory,
        ),
        now=COMMAND_INSTANT,
        read_clock=lambda: COMMAND_INSTANT,
        entry_point=root / "bin" / "brigade",
        trail=TrailWriter(_keep_no_trace),
        resolve_plugin=resolve_plugin,
    )
