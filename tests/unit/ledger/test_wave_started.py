import unittest

from brigade.ledger.wave_started import WaveStarted


class WaveStartedTest(unittest.TestCase):
    def test_should_read_the_start_of_a_wave(self):
        # Act
        event = WaveStarted.from_document({"event": "wave.started", "wave": "tp/16", "project": "tidepool"})

        # Assert
        self.assertEqual(event, WaveStarted(wave="tp/16", project="tidepool"))

    def test_should_write_the_wave_and_its_project(self):
        # Arrange
        event = WaveStarted(wave="M1", project="shop")

        # Act
        document = event.to_document()

        # Assert
        self.assertEqual(document, {"wave": "M1", "project": "shop"})
