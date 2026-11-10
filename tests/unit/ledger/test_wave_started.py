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

    def test_should_write_the_start_of_a_wave(self):
        # Arrange
        event = WaveStarted(wave="shop_w1", project="shop", branch="integration/M1-empty-cart", tasks=("S3", "S4"))

        # Act
        document = event.to_document()

        # Assert
        self.assertEqual(
            document,
            {"wave": "shop_w1", "project": "shop", "branch": "integration/M1-empty-cart", "tasks": ["S3", "S4"]},
        )

    def test_should_read_the_start_of_a_wave_with_no_branch(self):
        # Act
        event = WaveStarted.from_document(
            {"event": "wave.started", "wave": "tidepool_w17", "project": "tidepool", "tasks": ["T8"]}
        )

        # Assert
        self.assertEqual(event, WaveStarted(wave="tidepool_w17", project="tidepool", branch=None, tasks=("T8",)))

    def test_should_write_the_start_of_a_wave_with_no_branch(self):
        # Arrange
        event = WaveStarted(wave="shop_w2", project="shop", branch=None, tasks=("S5",))

        # Act
        document = event.to_document()

        # Assert
        self.assertEqual(document, {"wave": "shop_w2", "project": "shop", "tasks": ["S5"]})

    def test_should_read_the_digest_of_each_task_recorded_at_the_start_of_the_wave(self):
        # Act
        event = WaveStarted.from_document(
            {
                "event": "wave.started",
                "wave": "tidepool_w18",
                "project": "tidepool",
                "tasks": ["T8"],
                "task_digests": {"T8": "21b8"},
            }
        )

        # Assert
        self.assertEqual(event.task_digests, {"T8": "21b8"})

    def test_should_write_the_digest_of_each_task(self):
        # Arrange
        event = WaveStarted(wave="shop_w3", project="shop", branch=None, tasks=("S5",), task_digests={"S5": "21b8"})

        # Act
        document = event.to_document()

        # Assert
        self.assertEqual(
            document, {"wave": "shop_w3", "project": "shop", "tasks": ["S5"], "task_digests": {"S5": "21b8"}}
        )
