import unittest

from brigade.ledger.wave_started import WaveStarted


class WaveStartedTest(unittest.TestCase):
    def test_should_read_the_start_of_a_wave(self):
        # Act
        event = WaveStarted.from_document({"event": "wave.started", "wave": "tp/16", "project": "tidepool"})

        # Assert
        self.assertEqual(event, WaveStarted(wave="tp/16", project="tidepool"))
