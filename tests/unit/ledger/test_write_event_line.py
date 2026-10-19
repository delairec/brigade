import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.ledger.signal_recorded import SignalRecorded
from brigade.ledger.write_event_line import LedgerEventRefused, write_event_line
from brigade.system.paths import Paths

PARIS_SUMMER_TIME = timezone(timedelta(hours=2))
BUDGET_SIGNAL = SignalRecorded(
    signal="budget_reached",
    project="tidepool",
    procedure="deliver",
    run="20261006T093000Z-b74a01",
    segment=1,
    budget=40,
)


def create_paths(state_root: Path) -> Paths:
    root = state_root.parents[1]
    return Paths(
        config_root=root / "config" / "brigade",
        state_root=state_root,
        cache_root=root / "cache" / "brigade",
        home=root,
        executable_search_path="",
    )


class WriteEventLineTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.state_root = Path(self.root.name) / "state" / "brigade"
        self.ledger = self.state_root / "ledger"
        self.paths = create_paths(self.state_root)

    def tearDown(self):
        self.root.cleanup()


class WriteEventLineOfAnInstantWithATimeZoneTest(WriteEventLineTestCase):
    def test_should_create_the_ledger_and_append_the_versioned_line_to_the_month_file(self):
        # Arrange
        instant = datetime(2026, 10, 6, 9, 30, tzinfo=UTC)

        # Act
        write_event_line(self.paths, instant, BUDGET_SIGNAL)

        # Assert
        self.assertEqual(
            [json.loads(line) for line in (self.ledger / "2026-10.jsonl").read_text().splitlines()],
            [
                {
                    "schema_version": 1,
                    "ts": "2026-10-06T09:30:00Z",
                    "event": "signal.recorded",
                    "signal": "budget_reached",
                    "project": "tidepool",
                    "procedure": "deliver",
                    "run": "20261006T093000Z-b74a01",
                    "segment": 1,
                    "budget": 40,
                }
            ],
        )

    def test_should_return_the_line_it_appended(self):
        # Arrange
        instant = datetime(2026, 10, 6, 9, 30, tzinfo=UTC)

        # Act
        line = write_event_line(self.paths, instant, BUDGET_SIGNAL)

        # Assert
        self.assertEqual(line, json.loads((self.ledger / "2026-10.jsonl").read_text()))

    def test_should_write_the_instant_in_utc_into_the_file_of_its_utc_month(self):
        # Arrange
        instant = datetime(2026, 10, 1, 1, 30, tzinfo=PARIS_SUMMER_TIME)

        # Act
        write_event_line(self.paths, instant, BUDGET_SIGNAL)

        # Assert
        self.assertEqual(
            json.loads((self.ledger / "2026-09.jsonl").read_text())["ts"],
            "2026-09-30T23:30:00Z",
        )

    def test_should_append_after_the_lines_already_written(self):
        # Arrange
        self.ledger.mkdir(parents=True)
        earlier_line = (
            '{"schema_version": 1, "ts": "2026-10-01T08:00:00Z", "event": "wave.resumed", "wave": "tidepool_w16"}\n'
        )
        (self.ledger / "2026-10.jsonl").write_text(earlier_line)
        instant = datetime(2026, 10, 6, 9, 30, tzinfo=UTC)

        # Act
        write_event_line(self.paths, instant, BUDGET_SIGNAL)

        # Assert
        self.assertEqual(
            (self.ledger / "2026-10.jsonl").read_text(),
            earlier_line + '{"schema_version": 1, "ts": "2026-10-06T09:30:00Z", "event": "signal.recorded",'
            ' "signal": "budget_reached", "project": "tidepool", "procedure": "deliver",'
            ' "run": "20261006T093000Z-b74a01", "segment": 1, "budget": 40}\n',
        )


class WriteEventLineOfAnInstantWithNoTimeZoneTest(WriteEventLineTestCase):
    def test_should_refuse_an_instant_with_no_time_zone_and_write_nothing(self):
        # Arrange
        naive_instant = datetime(2026, 10, 6, 9, 30)  # noqa: DTZ001 - the instant with no time zone the ledger refuses

        # Act
        with self.assertRaises(LedgerEventRefused) as refusal:
            write_event_line(self.paths, naive_instant, BUDGET_SIGNAL)

        # Assert
        self.assertEqual(
            (str(refusal.exception), self.ledger.exists()),
            ("the instant of the event signal.recorded carries no time zone", False),
        )


class WriteEventLineWhereTheMachineRefusesTheWriteTest(WriteEventLineTestCase):
    def setUp(self):
        super().setUp()
        self.state_root.mkdir(parents=True)
        self.instant = datetime(2026, 10, 6, 9, 30, tzinfo=UTC)

    def test_should_name_the_ledger_directory_it_cannot_create(self):
        # Arrange
        self.ledger.touch()

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            write_event_line(self.paths, self.instant, BUDGET_SIGNAL)

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot write {self.ledger}: File exists")

    def test_should_name_the_month_file_it_cannot_open(self):
        # Arrange
        (self.ledger / "2026-10.jsonl").mkdir(parents=True)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            write_event_line(self.paths, self.instant, BUDGET_SIGNAL)

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot write {self.ledger / '2026-10.jsonl'}: Is a directory")
