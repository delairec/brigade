import unittest

from brigade.ledger.milestone_pr_described import MilestonePrDescribed
from brigade.waves.find_milestone_described_head import find_milestone_described_head

NO_EVENT = ()


class FindMilestoneDescribedHeadTest(unittest.TestCase):
    def test_should_find_the_head_of_the_last_description_of_the_pull_request_of_the_milestone(self):
        # Arrange
        events = (
            MilestonePrDescribed(project="tidepool", milestone="M4", pr=90, head="c4a7413f", login="tidepool-cli"),
            MilestonePrDescribed(project="tidepool", milestone="M4", pr=90, head="9010166d", login="tidepool-cli"),
        )

        # Act
        head = find_milestone_described_head(events, "tidepool", "M4", 90)

        # Assert
        self.assertEqual(head, "9010166d")

    def test_should_find_none(self):
        for case, events in [
            ("no description", NO_EVENT),
            (
                "a description of the milestone of another project",
                (MilestonePrDescribed(project="shop", milestone="M4", pr=90, head="c4a7413f", login=None),),
            ),
            (
                "a description of another milestone",
                (MilestonePrDescribed(project="tidepool", milestone="M5", pr=90, head="c4a7413f", login=None),),
            ),
            (
                "a description of another pull request of the milestone",
                (MilestonePrDescribed(project="tidepool", milestone="M4", pr=89, head="c4a7413f", login=None),),
            ),
        ]:
            with self.subTest(case=case):
                # Act
                head = find_milestone_described_head(events, "tidepool", "M4", 90)

                # Assert
                self.assertIsNone(head)


if __name__ == "__main__":
    unittest.main()
