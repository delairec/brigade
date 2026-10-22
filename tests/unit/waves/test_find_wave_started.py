import unittest

from brigade.ledger.wave_pr_opened import WavePrOpened
from brigade.ledger.wave_started import WaveStarted
from brigade.waves.find_wave_started import find_wave_started


class FindWaveStartedTest(unittest.TestCase):
    def test_should_find_the_start_of_the_wave_among_the_events_of_every_wave(self):
        # Arrange
        events = (
            WaveStarted(wave="shop_w1", project="shop", branch="integration/shop_w1", tasks=("S1",)),
            WavePrOpened(wave="shop_w2", pr=12, login="octo-bot"),
            WaveStarted(wave="shop_w2", project="shop", branch="integration/shop_w2", tasks=("S3",)),
        )

        # Act
        started = find_wave_started(events, "shop_w2")

        # Assert
        self.assertEqual(
            started, WaveStarted(wave="shop_w2", project="shop", branch="integration/shop_w2", tasks=("S3",))
        )
