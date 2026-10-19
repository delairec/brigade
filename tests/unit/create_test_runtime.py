from datetime import UTC, datetime
from pathlib import Path

from brigade.runtime import Runtime
from brigade.system.paths import Paths
from brigade.system.trail_writer import TrailWriter

FIXED_NOW = datetime(2026, 10, 19, 9, 0, tzinfo=UTC)


def refuse_to_run(request):
    raise AssertionError(f"{' '.join(request.argv)} should not run")


def refuse_to_spawn(request):
    raise AssertionError(f"{' '.join(request.argv)} should not be spawned")


def refuse_to_resolve(kind: str, name: str, *arguments):
    raise AssertionError(f"the {kind} plugin {name} should not be resolved")


def keep_no_trace(trace) -> None:
    pass


def create_test_paths(root: Path) -> Paths:
    return Paths(
        config_root=root / "config" / "brigade",
        state_root=root / "state" / "brigade",
        cache_root=root / "cache" / "brigade",
        home=root,
        executable_search_path="/usr/bin",
    )


def create_test_runtime(
    paths: Paths,
    run_process=refuse_to_run,
    spawn_process=refuse_to_spawn,
    resolve_plugin=refuse_to_resolve,
    now: datetime = FIXED_NOW,
    trail: TrailWriter | None = None,
) -> Runtime:
    return Runtime(
        run_process=run_process,
        spawn_process=spawn_process,
        paths=paths,
        now=now,
        read_clock=lambda: now,
        entry_point=Path("/srv/brigade/bin/brigade"),
        trail=TrailWriter(keep_no_trace) if trail is None else trail,
        resolve_plugin=resolve_plugin,
    )
