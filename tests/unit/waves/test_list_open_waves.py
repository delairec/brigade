import unittest
from datetime import UTC, datetime

from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.wave_cancelled import WaveCancelled
from brigade.ledger.wave_closed import WaveClosed
from brigade.ledger.wave_started import WaveStarted
from brigade.waves.list_open_waves import list_open_waves

INSTANT = datetime(2026, 10, 19, 9, 0, tzinfo=UTC)
CLOSED_WAVE = WaveStarted(wave="shop_w1", project="shop", branch="integration/shop_w1", tasks=("S3",))
CANCELLED_WAVE = WaveStarted(wave="shop_w2", project="shop", branch="integration/shop_w2", tasks=("S4",))
OPEN_WAVE = WaveStarted(wave="shop_w3", project="shop", branch="integration/shop_w3", tasks=("S5",))
OPEN_WAVE_OF_ANOTHER_PROJECT = WaveStarted(
    wave="depot_w1", project="depot", branch="integration/depot_w1", tasks=("D1",)
)


class ListOpenWavesTest(unittest.TestCase):
    def test_should_list_the_waves_of_the_project_neither_closed_nor_cancelled(self):
        # Arrange
        entries = (
            LedgerEntry(instant=INSTANT, event=CLOSED_WAVE),
            LedgerEntry(instant=INSTANT, event=WaveClosed(wave="shop_w1", pr=31)),
            LedgerEntry(instant=INSTANT, event=CANCELLED_WAVE),
            LedgerEntry(instant=INSTANT, event=WaveCancelled(wave="shop_w2", reason="user")),
            LedgerEntry(instant=INSTANT, event=OPEN_WAVE),
            LedgerEntry(instant=INSTANT, event=OPEN_WAVE_OF_ANOTHER_PROJECT),
        )

        # Act
        waves = list_open_waves(entries, "shop")

        # Assert
        self.assertEqual(
            waves,
            (WaveStarted(wave="shop_w3", project="shop", branch="integration/shop_w3", tasks=("S5",)),),
        )


if __name__ == "__main__":
    unittest.main()
