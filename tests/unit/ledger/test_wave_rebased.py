import unittest

from brigade.ledger.declared_events import DECLARED_EVENTS
from brigade.ledger.wave_rebased import WaveRebased


class WaveRebasedTest(unittest.TestCase):
    def test_should_read_the_rebase_of_a_wave_branch_with_its_heads_before_and_after(self):
        # Act
        event = WaveRebased.from_document(
            {
                "event": "wave.rebased",
                "project": "shop",
                "wave": "shop_w4",
                "branch": "integration/shop_w4",
                "before": "c3d9f04",
                "after": "e70f3a2",
                "login": "octo-bot",
            }
        )

        # Assert
        self.assertEqual(
            event,
            WaveRebased(
                project="shop",
                wave="shop_w4",
                branch="integration/shop_w4",
                before="c3d9f04",
                after="e70f3a2",
                login="octo-bot",
            ),
        )

    def test_should_write_the_wave_branch_its_heads_before_and_after_and_the_login(self):
        # Arrange
        event = WaveRebased(
            project="shop",
            wave="shop_w4",
            branch="integration/shop_w4",
            before="c3d9f04",
            after="e70f3a2",
            login=None,
        )

        # Act
        document = event.to_document()

        # Assert
        self.assertEqual(
            document,
            {
                "project": "shop",
                "wave": "shop_w4",
                "branch": "integration/shop_w4",
                "before": "c3d9f04",
                "after": "e70f3a2",
                "login": None,
            },
        )

    def test_should_be_declared_in_the_ledger(self):
        # Act
        declared = DECLARED_EVENTS.get("wave.rebased")

        # Assert
        self.assertIs(declared, WaveRebased)
