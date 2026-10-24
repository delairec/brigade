import json
import multiprocessing
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.ledger.append_event import append_event
from brigade.ledger.order_parked import OrderParked
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.signal_recorded import SignalRecorded
from brigade.ledger.step_done import StepDone
from brigade.ledger.step_failed import StepFailed
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
    writers = (
        context.Process(target=append_signals, args=(root, 0)),
        context.Process(target=append_signals, args=(root, 1)),
        context.Process(target=append_signals, args=(root, 2)),
        context.Process(target=append_signals, args=(root, 3)),
    )
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


class AppendEventOfAStudyRunTest(AppendEventTestCase):
    def test_should_write_one_line_naming_the_event(self):
        for event, expected in [
            (
                StepDone(kind="study", run="r1", step="collect"),
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "step.done",
                    "kind": "study",
                    "run": "r1",
                    "step": "collect",
                },
            ),
            (
                StepFailed(kind="study", run="r1", step="judge", reason="quota"),
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "step.failed",
                    "kind": "study",
                    "run": "r1",
                    "step": "judge",
                    "reason": "quota",
                },
            ),
            (
                OrderParked(project=None, kind="study", order="trees", run="r1", step="judge", reason="quota"),
                {
                    "schema_version": 1,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "order.parked",
                    "project": None,
                    "kind": "study",
                    "order": "trees",
                    "run": "r1",
                    "step": "judge",
                    "reason": "quota",
                },
            ),
        ]:
            with self.subTest(event=expected["event"]):
                # Arrange
                month = self.ledger / "2026-10.jsonl"
                month.unlink(missing_ok=True)

                # Act
                append_event(self.paths, datetime(2026, 10, 19, 9, 0, tzinfo=UTC), event)

                # Assert
                self.assertEqual(json.loads(month.read_text()), expected)
