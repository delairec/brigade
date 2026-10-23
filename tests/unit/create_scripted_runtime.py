from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from brigade.runtime import Runtime
from brigade.system.paths import Paths
from brigade.system.trail_writer import TrailWriter

RUNTIME_NOW = datetime(2026, 10, 19, 9, 0, tzinfo=UTC)
NO_SEARCH_PATH = ""


def _keep_no_trace(trace) -> None:
    pass


def _refuse_spawn(request):
    raise AssertionError(f"the code under test spawned {request.argv}")


def _refuse_resolution(*arguments, **options):
    raise AssertionError(f"the code under test resolved the plugin {arguments}")


def create_scripted_runtime(
    root: Path,
    run_process: Callable,
    run_directory: Path | None = None,
    executable_search_path: str = NO_SEARCH_PATH,
    spawn_process: Callable = _refuse_spawn,
) -> Runtime:
    paths = Paths(
        config_root=root / "config",
        state_root=root / "state",
        cache_root=root / "cache",
        home=root / "home",
        executable_search_path=executable_search_path,
        run_directory=run_directory,
    )
    paths.config_root.mkdir(parents=True, exist_ok=True)
    paths.schema_file.write_text("", encoding="utf-8")
    return Runtime(
        run_process=run_process,
        spawn_process=spawn_process,
        paths=paths,
        now=RUNTIME_NOW,
        read_clock=lambda: RUNTIME_NOW,
        read_monotonic=lambda: 0.0,
        entry_point=root / "bin" / "brigade",
        trail=TrailWriter(_keep_no_trace),
        resolve_plugin=_refuse_resolution,
    )
