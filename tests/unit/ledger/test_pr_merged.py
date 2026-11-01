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
                "login": "tidepool-cli",
            }
        )

        # Assert
        self.assertEqual(
            event,
            PrMerged(project="tidepool", wave="tidepool_w16", task="TP146", pr=291, rounds=1, login="tidepool-cli"),
        )


class PrMergedWithoutAPullRequestTest(unittest.TestCase):
    def test_should_read_the_local_merge_of_a_task(self):
        # Act
        event = PrMerged.from_document(
            {"event": "pr.merged", "project": "shop", "wave": "shop_w2", "task": "S4", "rounds": 0, "login": None}
        )

        # Assert
        self.assertEqual(event, PrMerged(project="shop", wave="shop_w2", task="S4", pr=None, rounds=0, login=None))

    def test_should_write_the_local_merge_of_a_task_with_the_pull_request_absent(self):
        # Arrange
        event = PrMerged(project="shop", wave="shop_w2", task="S4", pr=None, rounds=0, login=None)

        # Act
        document = event.to_document()

        # Assert
        self.assertEqual(document, {"project": "shop", "wave": "shop_w2", "task": "S4", "rounds": 0, "login": None})
