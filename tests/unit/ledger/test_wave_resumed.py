import unittest

from brigade.ledger.wave_resumed import WaveResumed


class WaveResumedTest(unittest.TestCase):
    def test_should_read_the_resumption_of_a_wave_and_the_reason_of_its_pause(self):
        # Act
        event = WaveResumed.from_document({"event": "wave.resumed", "wave": "tidepool_w16", "reason": "quota"})

        # Assert
        self.assertEqual(event, WaveResumed(wave="tidepool_w16", reason="quota"))

    def test_should_write_the_resumption_of_a_wave(self):
        # Arrange
        event = WaveResumed(wave="tidepool_w16", reason="forge_account")

        # Act
        document = event.to_document()

        # Assert
        self.assertEqual(document, {"wave": "tidepool_w16", "reason": "forge_account"})
