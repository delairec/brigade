import unittest
from datetime import UTC, datetime

from brigade.errors import BrigadeError
from brigade.ledger.describe_task import describe_task
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.read_ledger import LedgerReading
from brigade.ledger.wave_started import WaveStarted
from tests.unit.ledger.create_run_finished import create_run_finished


def at_minute(minute: int) -> datetime:
    return datetime(2026, 10, 10, 9, minute, tzinfo=UTC)


def create_reading(*entries: LedgerEntry) -> LedgerReading:
    return LedgerReading(entries=entries, files=(), skipped=())


class DescribeTaskTest(unittest.TestCase):
    def test_should_present_each_run_of_the_task_by_its_segments(self):
        # Arrange
        reading = create_reading(
            LedgerEntry(at_minute(0), WaveStarted(wave="w1", project="tidepool", branch="main", tasks=("TP1",))),
            LedgerEntry(
                at_minute(1),
                create_run_finished(
                    "r1",
                    segment=1,
                    main_steps=10,
                    outcome="budget_reached",
                    task="TP1",
                    duration_ms=60000,
                    cost_usd=3.5,
                ),
            ),
            LedgerEntry(at_minute(2), create_run_finished("r9", main_steps=99, task="TP2", cost_usd=9.0)),
            LedgerEntry(
                at_minute(3),
                create_run_finished("r1", segment=2, main_steps=5, task="TP1", duration_ms=30000, cost_usd=1.25),
            ),
            LedgerEntry(
                at_minute(4),
                create_run_finished("r2", slot="review", outcome="failed", task="TP1", duration_ms=None),
            ),
        )

        # Act
        description = describe_task(reading, "TP1")

        # Assert
        self.assertEqual(
            description,
            {
                "view": "task",
                "task": "TP1",
                "runs": [
                    {
                        "run": "r1",
                        "finished_at": "2026-10-10T09:03:00Z",
                        "slot": "build",
                        "outcome": "succeeded",
                        "steps": 15,
                        "partial": False,
                        "duration_ms": 90000,
                        "cost_usd": 4.75,
                    },
                    {
                        "run": "r2",
                        "finished_at": "2026-10-10T09:04:00Z",
                        "slot": "review",
                        "outcome": "failed",
                        "steps": None,
                        "partial": False,
                        "duration_ms": None,
                        "cost_usd": None,
                    },
                ],
            },
        )

    def test_should_mark_partial_a_run_one_of_whose_segments_is_not_measured(self):
        # Arrange
        reading = create_reading(
            LedgerEntry(at_minute(1), create_run_finished("r1", segment=1, main_steps=10, task="TP1")),
            LedgerEntry(at_minute(2), create_run_finished("r1", segment=2, task="TP1")),
        )

        # Act
        description = describe_task(reading, "TP1")

        # Assert
        self.assertEqual(description["runs"][0]["partial"], True)

    def test_should_refuse_a_task_no_run_names(self):
        # Arrange
        reading = create_reading(LedgerEntry(at_minute(1), create_run_finished("r9", task="TP2")))

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            describe_task(reading, "TP1")

        # Assert
        self.assertEqual(str(refusal.exception), "no run names the task TP1")
