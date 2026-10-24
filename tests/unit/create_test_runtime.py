from datetime import UTC, datetime
from pathlib import Path

from brigade.runtime import Runtime
from brigade.system.paths import Paths
from brigade.system.poll_until_signalled import poll_until_signalled as poll_until_really_signalled
from brigade.system.trail_writer import TrailWriter
from tests.unit.create_test_paths import create_test_paths
from tests.unit.refuse_to_run import refuse_to_run

FIXED_NOW = datetime(2026, 10, 19, 9, 0, tzinfo=UTC)
UNWRITTEN_PATHS = create_test_paths(Path("/nonexistent"))


def _refuse_to_spawn(request):
    raise AssertionError(f"{' '.join(request.argv)} should not be spawned")


def _refuse_to_resolve(kind: str, name: str, *arguments):
    raise AssertionError(f"the {kind} plugin {name} should not be resolved")


def _keep_no_trace(trace) -> None:
    pass


def create_test_runtime(
    paths: Paths = UNWRITTEN_PATHS,
    run_process=refuse_to_run,
    spawn_process=_refuse_to_spawn,
    resolve_plugin=_refuse_to_resolve,
    now: datetime = FIXED_NOW,
    trail: TrailWriter | None = None,
    poll_until_signalled=poll_until_really_signalled,
) -> Runtime:
    return Runtime(
        run_process=run_process,
        spawn_process=spawn_process,
        paths=paths,
        now=now,
        read_clock=lambda: now,
        read_monotonic=lambda: 0.0,
        entry_point=Path("/srv/brigade/bin/brigade"),
        trail=TrailWriter(_keep_no_trace) if trail is None else trail,
        resolve_plugin=resolve_plugin,
        poll_until_signalled=poll_until_signalled,
    )
