import unittest

from brigade.ledger.declared_events import DECLARED_EVENTS
from brigade.ledger.wave_pr_retargeted import WavePrRetargeted


class WavePrRetargetedTest(unittest.TestCase):
    def test_should_read_the_pull_request_of_a_wave_retargeted_onto_a_base(self):
        # Act
        event = WavePrRetargeted.from_document(
            {
                "event": "wave.pr_retargeted",
                "wave": "brigade_w4",
                "pr": 237,
                "base": "integration/dashboard",
                "login": "octo-bot",
            }
        )

        # Assert
        self.assertEqual(
            event, WavePrRetargeted(wave="brigade_w4", pr=237, base="integration/dashboard", login="octo-bot")
        )

    def test_should_write_the_wave_the_pull_request_the_base_and_the_login(self):
        # Arrange
        event = WavePrRetargeted(wave="brigade_w4", pr=237, base="integration/dashboard", login=None)

        # Act
        document = event.to_document()

        # Assert
        self.assertEqual(document, {"wave": "brigade_w4", "pr": 237, "base": "integration/dashboard", "login": None})

    def test_should_be_declared_in_the_ledger(self):
        # Act
        declared = DECLARED_EVENTS.get("wave.pr_retargeted")

        # Assert
        self.assertIs(declared, WavePrRetargeted)
