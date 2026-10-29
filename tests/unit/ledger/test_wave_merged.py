import unittest

from brigade.ledger.declared_events import DECLARED_EVENTS
from brigade.ledger.wave_merged import WaveMerged


class WaveMergedTest(unittest.TestCase):
    def test_should_read_the_merge_of_the_pull_request_of_a_wave(self):
        # Act
        event = WaveMerged.from_document({"event": "wave.merged", "wave": "shop_w2", "pr": 41, "login": "octo-bot"})

        # Assert
        self.assertEqual(event, WaveMerged(wave="shop_w2", pr=41, login="octo-bot"))

    def test_should_write_the_wave_the_pull_request_and_the_login(self):
        # Arrange
        event = WaveMerged(wave="shop_w2", pr=41, login="octo-bot")

        # Act
        document = event.to_document()

        # Assert
        self.assertEqual(document, {"wave": "shop_w2", "pr": 41, "login": "octo-bot"})

    def test_should_be_declared_in_the_ledger(self):
        # Act
        declared = DECLARED_EVENTS.get("wave.merged")

        # Assert
        self.assertIs(declared, WaveMerged)
