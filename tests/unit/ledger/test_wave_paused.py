import unittest

from brigade.ledger.wave_paused import WavePaused


class WavePausedTest(unittest.TestCase):
    def test_should_read_the_pause_of_a_wave(self):
        # Act
        event = WavePaused.from_document({"event": "wave.paused", "wave": "tp/16"})

        # Assert
        self.assertEqual(event, WavePaused(wave="tp/16"))
