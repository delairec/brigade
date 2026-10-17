import unittest
from datetime import UTC, datetime

from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.task_state import TaskState
from brigade.ledger.wave_started import WaveStarted
from brigade.waves.name_next_wave import name_next_wave

INSTANT = datetime(2026, 10, 13, 9, 0, tzinfo=UTC)


class NameNextWaveTest(unittest.TestCase):
    def test_should_number_the_first_wave_of_a_project_1(self):
        # Arrange
        no_entries = ()

        # Act
        name = name_next_wave("shop", no_entries)

        # Assert
        self.assertEqual(name, "shop_w1")

    def test_should_number_a_wave_one_above_the_highest_wave_of_its_project(self):
        # Arrange
        entries = (
            LedgerEntry(
                instant=INSTANT,
                event=WaveStarted(wave="shop_w10", project="shop", branch="integration/M1-empty-cart", tasks=("S3",)),
            ),
            LedgerEntry(
                instant=INSTANT,
                event=WaveStarted(wave="cafe_w12", project="cafe", branch="integration/M1-receipt", tasks=("C1",)),
            ),
            LedgerEntry(
                instant=INSTANT,
                event=WaveStarted(wave="shop_w9", project="shop", branch="integration/M2-undo", tasks=("S5",)),
            ),
            LedgerEntry(instant=INSTANT, event=TaskState(wave="shop_w10", task="S3", state="running")),
        )

        # Act
        name = name_next_wave("shop", entries)

        # Assert
        self.assertEqual(name, "shop_w11")
