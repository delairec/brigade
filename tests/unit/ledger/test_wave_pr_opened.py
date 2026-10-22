import unittest

from brigade.ledger.wave_pr_opened import WavePrOpened


class WavePrOpenedTest(unittest.TestCase):
    def test_should_read_the_integration_pull_request_opened_for_a_wave(self):
        # Act
        event = WavePrOpened.from_document(
            {"event": "wave.pr_opened", "wave": "tidepool_w16", "pr": 77, "login": "tidepool-cli"}
        )

        # Assert
        self.assertEqual(event, WavePrOpened(wave="tidepool_w16", pr=77, login="tidepool-cli"))

    def test_should_write_the_wave_the_pull_request_and_the_login(self):
        # Arrange
        event = WavePrOpened(wave="tidepool_w16", pr=77, login="tidepool-cli")

        # Act
        document = event.to_document()

        # Assert
        self.assertEqual(document, {"wave": "tidepool_w16", "pr": 77, "login": "tidepool-cli"})


if __name__ == "__main__":
    unittest.main()
