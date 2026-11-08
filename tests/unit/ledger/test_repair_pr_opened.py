import unittest

from brigade.ledger.declared_events import DECLARED_EVENTS
from brigade.ledger.repair_pr_opened import RepairPrOpened

OPENED = RepairPrOpened(project="oak", branch="fix/repair-main-c0ffee", into="main", pr=91, login="fix-bot")
DOCUMENT = {"project": "oak", "branch": "fix/repair-main-c0ffee", "into": "main", "pr": 91, "login": "fix-bot"}


class RepairPrOpenedTest(unittest.TestCase):
    def test_should_read_the_pull_request_opened_for_the_repair_of_a_main_branch(self):
        # Act
        event = RepairPrOpened.from_document({"event": "repair.pr_opened", **DOCUMENT})

        # Assert
        self.assertEqual(event, OPENED)

    def test_should_write_the_project_the_branch_its_main_branch_the_pull_request_and_the_login(self):
        # Act
        document = OPENED.to_document()

        # Assert
        self.assertEqual(document, DOCUMENT)

    def test_should_be_declared_in_the_ledger(self):
        # Act
        declared = DECLARED_EVENTS.get("repair.pr_opened")

        # Assert
        self.assertIs(declared, RepairPrOpened)


if __name__ == "__main__":
    unittest.main()
