import unittest

from brigade.ledger.wave_parked import WaveParked


class WaveParkedTest(unittest.TestCase):
    def test_should_read_a_wave_parked_on_the_forge_account(self):
        # Act
        event = WaveParked.from_document({"event": "wave.parked", "wave": "tidepool_w16", "reason": "forge_account"})

        # Assert
        self.assertEqual(event, WaveParked(wave="tidepool_w16", reason="forge_account"))

    def test_should_write_a_wave_parked_on_the_forge_account(self):
        # Arrange
        event = WaveParked(wave="tidepool_w16", reason="forge_account")

        # Act
        document = event.to_document()

        # Assert
        self.assertEqual(document, {"wave": "tidepool_w16", "reason": "forge_account"})
