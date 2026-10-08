import contextlib
import io
import os
import signal
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from brigade.commands.tick import COMMAND
from brigade.runtime import Runtime
from brigade.system.paths import Paths
from brigade.system.trail_writer import TrailWriter

LOOP_MODE = "loop"
NO_PATH_NEEDED = ""
WAKE_THE_LOOP = signal.SIGUSR1


def _report_nothing(trace) -> None:
    pass


def _refuse_process(request):
    raise AssertionError(f"a round of tick ran {request.argv}")


def _refuse_resolution(kind: str, name: str):
    raise AssertionError(f"a round of tick resolved the {kind} plugin {name}")


def _ignore_signal(_received, _frame) -> None:
    pass


def _create_runtime(root: Path, now: datetime) -> Runtime:
    return Runtime(
        run_process=_refuse_process,
        spawn_process=_refuse_process,
        paths=Paths(
            config_root=root / "config",
            state_root=root / "state",
            cache_root=root / "cache",
            home=root / "home",
            executable_search_path=NO_PATH_NEEDED,
        ),
        now=now,
        entry_point=root / "bin" / "brigade",
        trail=TrailWriter(_report_nothing),
        resolve_plugin=_refuse_resolution,
    )


def _create_round_factory(rounds: list[tuple[Runtime, signal.Signals]]):
    remaining = iter(rounds)

    def create_runtime() -> Runtime:
        runtime, signal_to_receive = next(remaining)
        os.kill(os.getpid(), signal_to_receive)
        return runtime

    return create_runtime


class TickLoopTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        previous_handler = signal.signal(WAKE_THE_LOOP, _ignore_signal)
        self.addCleanup(signal.signal, signal.SIGUSR1, previous_handler)

    def test_should_give_each_round_a_runtime_of_its_own(self):
        # Arrange
        first_round = _create_runtime(self.root, datetime(2026, 10, 7, 9, 0, 0, tzinfo=UTC))
        second_round = _create_runtime(self.root, datetime(2026, 10, 7, 9, 5, 0, tzinfo=UTC))
        request = SimpleNamespace(
            mode=LOOP_MODE,
            create_runtime=_create_round_factory([(first_round, WAKE_THE_LOOP), (second_round, signal.SIGTERM)]),
        )
        command_runtime = _create_runtime(self.root, datetime(2026, 10, 7, 8, 59, 0, tzinfo=UTC))

        # Act
        with contextlib.redirect_stderr(io.StringIO()):
            COMMAND.run(request, command_runtime)

        # Assert
        self.assertCountEqual(
            os.listdir(self.root / "state" / "ticks"), ["20261007T090000Z.jsonl", "20261007T090500Z.jsonl"]
        )
