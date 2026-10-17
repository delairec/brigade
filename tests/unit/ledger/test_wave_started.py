import unittest

from brigade.ledger.wave_started import WaveStarted


class WaveStartedTest(unittest.TestCase):
    def test_should_read_the_start_of_a_wave(self):
        # Act
        event = WaveStarted.from_document(
            {
                "event": "wave.started",
                "wave": "tidepool_w16",
                "project": "tidepool",
                "branch": "integration/M4-tides",
                "tasks": ["T7", "T12"],
            }
        )

        # Assert
        self.assertEqual(
            event,
            WaveStarted(wave="tidepool_w16", project="tidepool", branch="integration/M4-tides", tasks=("T7", "T12")),
        )

    def test_should_write_the_wave_its_project_its_branch_and_its_tasks(self):
        # Arrange
        event = WaveStarted(wave="shop_w1", project="shop", branch="integration/M1-empty-cart", tasks=("S3", "S4"))

        # Act
        document = event.to_document()

        # Assert
        self.assertEqual(
            document,
            {"wave": "shop_w1", "project": "shop", "branch": "integration/M1-empty-cart", "tasks": ["S3", "S4"]},
        )
