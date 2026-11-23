import unittest
from datetime import UTC, datetime

from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.task_state import TaskState
from brigade.ledger.wave_cancelled import WaveCancelled
from brigade.ledger.wave_closed import WaveClosed
from brigade.ledger.wave_started import WaveStarted
from brigade.waves.describe_last_closed_wave import describe_last_closed_wave


def at(hour: int, minute: int) -> datetime:
    return datetime(2026, 10, 19, hour, minute, tzinfo=UTC)


OAK_W1_STARTED = LedgerEntry(
    at(1, 0), WaveStarted(wave="oak_w1", project="oak", branch="integration/m1", tasks=("B1",))
)
OAK_W1_CLOSED = LedgerEntry(at(1, 30), WaveClosed(wave="oak_w1"))


class DescribeLastClosedWaveTest(unittest.TestCase):
    def test_should_name_the_wave_closed_last_with_its_end_and_the_tasks_it_merged(self):
        # Arrange
        entries = (
            OAK_W1_STARTED,
            LedgerEntry(
                at(2, 0), WaveStarted(wave="oak_w2", project="oak", branch="integration/m1", tasks=("B2", "B3"))
            ),
            OAK_W1_CLOSED,
            LedgerEntry(at(2, 40), TaskState(wave="oak_w2", task="B2", state="merged", reason=None)),
            LedgerEntry(at(2, 50), TaskState(wave="oak_w2", task="B3", state="parked", reason="a question")),
            LedgerEntry(at(3, 0), WaveClosed(wave="oak_w2", pr=12)),
        )

        # Act
        described = describe_last_closed_wave(entries)

        # Assert
        self.assertEqual(
            described,
            {"wave": "oak_w2", "project": "oak", "closed_at": "2026-10-19T03:00:00Z", "tasks": 2, "merged": 1},
        )

    def test_should_name_no_wave_when_none_closed(self):
        # Arrange
        entries = (OAK_W1_STARTED, LedgerEntry(at(1, 30), WaveCancelled(wave="oak_w1", reason="planned again")))

        # Act
        described = describe_last_closed_wave(entries)

        # Assert
        self.assertIsNone(described)

    def test_should_pass_over_a_closed_wave_whose_start_the_ledger_lacks(self):
        # Arrange
        entries = (OAK_W1_STARTED, OAK_W1_CLOSED, LedgerEntry(at(4, 0), WaveClosed(wave="oak_w9")))

        # Act
        described = describe_last_closed_wave(entries)

        # Assert
        self.assertEqual(
            described,
            {"wave": "oak_w1", "project": "oak", "closed_at": "2026-10-19T01:30:00Z", "tasks": 1, "merged": 0},
        )
