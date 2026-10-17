import unittest

from brigade.ledger.wave_resumed import WaveResumed


class WaveResumedTest(unittest.TestCase):
    def test_should_read_the_resumption_of_a_wave(self):
        # Act
        event = WaveResumed.from_document({"event": "wave.resumed", "wave": "tidepool_w16"})

        # Assert
        self.assertEqual(event, WaveResumed(wave="tidepool_w16"))
