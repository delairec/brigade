import unittest

from brigade.ledger.pr_merged import PrMerged


class PrMergedTest(unittest.TestCase):
    def test_should_read_the_pull_request_merged_by_a_wave(self):
        # Act
        event = PrMerged.from_document(
            {
                "event": "pr.merged",
                "project": "tidepool",
                "wave": "tidepool_w16",
                "task": "TP146",
                "pr": 291,
                "rounds": 1,
            }
        )

        # Assert
        self.assertEqual(event, PrMerged(project="tidepool", wave="tidepool_w16", task="TP146", pr=291, rounds=1))
