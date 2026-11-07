import unittest

from brigade.ledger.wave_closed import WaveClosed


class WaveClosedTest(unittest.TestCase):
    def test_should_read_the_closing_of_a_wave_with_no_pull_request(self):
        # Act
        event = WaveClosed.from_document({"event": "wave.closed", "wave": "tidepool_w17"})

        # Assert
        self.assertEqual(event, WaveClosed(wave="tidepool_w17", pr=None))

    def test_should_still_read_the_closing_of_a_wave_by_its_pull_request(self):
        # Act
        event = WaveClosed.from_document({"event": "wave.closed", "wave": "tidepool_w16", "pr": 302})

        # Assert
        self.assertEqual(event, WaveClosed(wave="tidepool_w16", pr=302))

    def test_should_write_the_closing_of_a_wave_with_no_pull_request(self):
        # Arrange
        event = WaveClosed(wave="shop_w2")

        # Act
        document = event.to_document()

        # Assert
        self.assertEqual(document, {"wave": "shop_w2"})
