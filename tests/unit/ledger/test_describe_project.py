import unittest
from datetime import UTC, datetime

from brigade.ledger.constraint_delivered import ConstraintDelivered
from brigade.ledger.describe_project import describe_project
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.order_done import OrderDone
from brigade.ledger.pattern_ratified import PatternRatified
from brigade.ledger.pr_merged import PrMerged
from brigade.ledger.read_ledger import LedgerReading
from brigade.ledger.signal_recorded import SignalRecorded
from brigade.ledger.wave_started import WaveStarted

LATER = datetime(2026, 10, 6, 9, 0, tzinfo=UTC)


def create_reading(*entries: LedgerEntry) -> LedgerReading:
    return LedgerReading(entries=entries, files=(), skipped=())


class DescribeProjectTest(unittest.TestCase):
    def test_should_count_what_happened_to_the_project(self):
        # Arrange
        reading = create_reading(
            LedgerEntry(instant=datetime(2026, 10, 1, 9, 0, tzinfo=UTC), event=OrderDone(project="shop", kind="sweep")),
            LedgerEntry(instant=LATER, event=OrderDone(project="shop", kind="sweep")),
            LedgerEntry(instant=LATER, event=OrderDone(project="shop", kind="study")),
            LedgerEntry(instant=LATER, event=OrderDone(project="tidepool", kind="sweep")),
            LedgerEntry(instant=LATER, event=WaveStarted(wave="w1", project="shop", branch="main", tasks=("B1",))),
            LedgerEntry(
                instant=LATER, event=PrMerged(project="shop", wave="w1", task="B1", pr=7, rounds=1, login=None)
            ),
            LedgerEntry(
                instant=LATER,
                event=SignalRecorded(
                    signal="over_budget", project="shop", procedure="awawa-task", run="r1", segment=1, budget=40
                ),
            ),
            LedgerEntry(instant=LATER, event=PatternRatified(project="shop")),
            LedgerEntry(instant=LATER, event=ConstraintDelivered(project="shop")),
        )

        # Act
        description = describe_project(reading, "shop")

        # Assert
        self.assertEqual(
            description,
            {
                "view": "project",
                "project": "shop",
                "orders_done": {"study": 1, "sweep": 2},
                "waves_started": 1,
                "pull_requests_merged": 1,
                "signals_recorded": 1,
                "patterns_ratified": 1,
                "constraints_delivered": 1,
            },
        )
