import unittest

from brigade.ledger.declared_events import DECLARED_EVENTS
from brigade.ledger.wave_pr_described import WavePrDescribed


class WavePrDescribedTest(unittest.TestCase):
    def test_should_read_the_head_at_which_the_pull_request_of_a_wave_was_described(self):
        # Act
        event = WavePrDescribed.from_document(
            {
                "event": "wave.pr_described",
                "wave": "tidepool_w16",
                "pr": 77,
                "head": "c4a7413f",
                "login": "tidepool-cli",
            }
        )

        # Assert
        self.assertEqual(event, WavePrDescribed(wave="tidepool_w16", pr=77, head="c4a7413f", login="tidepool-cli"))

    def test_should_write_the_wave_the_pull_request_the_head_and_the_login(self):
        # Arrange
        event = WavePrDescribed(wave="tidepool_w16", pr=77, head="c4a7413f", login="tidepool-cli")

        # Act
        document = event.to_document()

        # Assert
        self.assertEqual(document, {"wave": "tidepool_w16", "pr": 77, "head": "c4a7413f", "login": "tidepool-cli"})

    def test_should_be_declared_in_the_ledger(self):
        # Act
        declared = DECLARED_EVENTS.get("wave.pr_described")

        # Assert
        self.assertIs(declared, WavePrDescribed)


if __name__ == "__main__":
    unittest.main()
