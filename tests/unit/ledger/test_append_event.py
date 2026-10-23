import json
import multiprocessing
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.ledger.append_event import append_event
from brigade.ledger.signal_recorded import SignalRecorded
from brigade.system.paths import Paths
from tests.unit.create_test_paths import PACKAGE_FILE

PROCESS_COUNT = 4
EVENTS_PER_PROCESS = 50
PADDING_LONGER_THAN_A_PIPE_BUFFER = "x" * 20000


def create_paths(state_root: Path) -> Paths:
    root = state_root.parents[1]
    return Paths(
        config_root=root / "config" / "brigade",
        state_root=state_root,
        cache_root=root / "cache" / "brigade",
        home=root,
        executable_search_path="",
        package_file=PACKAGE_FILE,
    )


def append_signals(state_root: Path, writer: int) -> None:
    for index in range(EVENTS_PER_PROCESS):
        append_event(
            create_paths(state_root),
            datetime(2026, 10, 6, 9, 30, tzinfo=UTC),
            SignalRecorded(
                signal="budget_reached",
                project="tidepool",
                procedure=PADDING_LONGER_THAN_A_PIPE_BUFFER,
                run=f"w{writer}-{index}",
                segment=1,
                budget=40,
            ),
        )


def append_from_concurrent_writers(state_root: Path) -> None:
    context = multiprocessing.get_context("fork")
    writers = [context.Process(target=append_signals, args=(state_root, writer)) for writer in range(PROCESS_COUNT)]
    for writer in writers:
        writer.start()
    for writer in writers:
        writer.join()


def read_distinct_runs(ledger_file: Path) -> set[str]:
    return {json.loads(line)["run"] for line in ledger_file.read_text().splitlines()}


class AppendEventTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.state_root = Path(self.root.name) / "state" / "brigade"
        self.ledger = self.state_root / "ledger"
        self.paths = create_paths(self.state_root)

    def tearDown(self):
        self.root.cleanup()


class AppendEventFromSeveralProcessesTest(AppendEventTestCase):
    def test_should_leave_every_line_whole(self):
        # Act
        append_from_concurrent_writers(self.state_root)

        # Assert
        self.assertEqual(len(read_distinct_runs(self.ledger / "2026-10.jsonl")), 200)
