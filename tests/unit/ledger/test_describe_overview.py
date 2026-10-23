import unittest
from datetime import UTC, datetime

from brigade.ledger.describe_overview import describe_overview
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.read_ledger import LedgerReading
from brigade.ledger.wave_started import WaveStarted
from tests.unit.ledger.create_run_finished import create_run_finished


class DescribeOverviewTest(unittest.TestCase):
    def test_should_count_the_events_and_the_outcomes_of_runs_and_segments(self):
        # Arrange
        reading = LedgerReading(
            entries=(
                LedgerEntry(
                    instant=datetime(2026, 10, 2, 9, 0, tzinfo=UTC),
                    event=WaveStarted(wave="w1", project="tidepool", branch="main", tasks=("TP1",)),
                ),
                LedgerEntry(
                    instant=datetime(2026, 10, 1, 9, 0, tzinfo=UTC),
                    event=create_run_finished("r1", segment=1, outcome="wall_limit"),
                ),
                LedgerEntry(
                    instant=datetime(2026, 10, 3, 9, 0, tzinfo=UTC),
                    event=create_run_finished("r1", segment=2, outcome="failed", error_class="ToolFailure"),
                ),
            ),
            files=("/state/ledger/2026-10.jsonl",),
            skipped=(),
        )

        # Act
        overview = describe_overview(reading)

        # Assert
        self.assertEqual(
            overview,
            {
                "view": "overview",
                "events": {"run.finished": 2, "wave.started": 1},
                "first": "2026-10-01T09:00:00Z",
                "last": "2026-10-03T09:00:00Z",
                "files": ["/state/ledger/2026-10.jsonl"],
                "runs": {"outcomes": {"failed": 1}, "error_classes": {"ToolFailure": 1}},
                "segments": {"outcomes": {"failed": 1, "wall_limit": 1}, "error_classes": {"ToolFailure": 1}},
            },
        )

    def test_should_leave_the_first_and_last_instants_empty_for_an_empty_ledger(self):
        # Arrange
        empty_reading = LedgerReading(entries=(), files=(), skipped=())

        # Act
        overview = describe_overview(empty_reading)

        # Assert
        self.assertEqual(overview["first"], None)
        self.assertEqual(overview["last"], None)
