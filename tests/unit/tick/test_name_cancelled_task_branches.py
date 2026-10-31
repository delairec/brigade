import unittest
from datetime import UTC, datetime

from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.wave_cancelled import WaveCancelled
from brigade.ledger.wave_closed import WaveClosed
from brigade.ledger.wave_started import WaveStarted
from brigade.tick.name_cancelled_task_branches import name_cancelled_task_branches

INSTANT = datetime(2026, 10, 28, 19, 45, tzinfo=UTC)


class NameCancelledTaskBranchesTest(unittest.TestCase):
    def test_should_name_the_branch_of_the_task_in_each_cancelled_wave_of_the_project(self):
        # Arrange
        entries = (
            LedgerEntry(
                instant=INSTANT,
                event=WaveStarted(wave="shop_w1", project="shop", branch="integration/shop_w1", tasks=("S3",)),
            ),
            LedgerEntry(instant=INSTANT, event=WaveClosed(wave="shop_w1", pr=31)),
            LedgerEntry(
                instant=INSTANT,
                event=WaveStarted(wave="shop_w2", project="shop", branch="integration/shop_w2", tasks=("S3",)),
            ),
            LedgerEntry(instant=INSTANT, event=WaveCancelled(wave="shop_w2", reason="user")),
            LedgerEntry(
                instant=INSTANT,
                event=WaveStarted(wave="shop_w3", project="shop", branch="integration/shop_w3", tasks=("S3",)),
            ),
            LedgerEntry(
                instant=INSTANT,
                event=WaveStarted(wave="depot_w1", project="depot", branch="integration/depot_w1", tasks=("S3",)),
            ),
            LedgerEntry(instant=INSTANT, event=WaveCancelled(wave="depot_w1", reason="user")),
        )

        # Act
        branches = name_cancelled_task_branches(entries, "shop", "S3")

        # Assert
        self.assertEqual(branches, frozenset({"task/shop_w2/S3"}))
