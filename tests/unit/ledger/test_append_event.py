import multiprocessing
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.ledger.append_event import append_event
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.signal_recorded import SignalRecorded
from tests.unit.create_test_paths import create_test_paths

PROCESS_COUNT = 4
EVENTS_PER_PROCESS = 50
PADDING_LONGER_THAN_A_PIPE_BUFFER = "x" * 20000


def append_signals(root: Path, writer: int) -> None:
    for index in range(EVENTS_PER_PROCESS):
        append_event(
            create_test_paths(root),
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


def append_from_concurrent_writers(root: Path) -> None:
    context = multiprocessing.get_context("fork")
    writers = [context.Process(target=append_signals, args=(root, writer)) for writer in range(PROCESS_COUNT)]
    for writer in writers:
        writer.start()
    for writer in writers:
        writer.join()


class AppendEventTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.paths = create_test_paths(Path(self.root.name))
        self.ledger = self.paths.state_root / "ledger"

    def tearDown(self):
        self.root.cleanup()


class AppendEventFromSeveralProcessesTest(AppendEventTestCase):
    def test_should_leave_every_line_whole(self):
        # Arrange
        append_from_concurrent_writers(Path(self.root.name))

        # Act
        reading = read_ledger(self.paths.state_root)

        # Assert
        self.assertEqual(reading.skipped, ())
        self.assertEqual(len(reading.entries), 200)
