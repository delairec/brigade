import unittest

from brigade.ledger.milestone_created import MilestoneCreated


class MilestoneCreatedTest(unittest.TestCase):
    def test_should_read_the_milestone_created_on_the_forge(self):
        # Act
        event = MilestoneCreated.from_document(
            {"event": "milestone.created", "project": "shop", "title": "Empty cart", "login": "octo-bot"}
        )

        # Assert
        self.assertEqual(event, MilestoneCreated(project="shop", title="Empty cart", login="octo-bot"))

    def test_should_write_the_project_the_title_and_the_login(self):
        # Arrange
        event = MilestoneCreated(project="shop", title="Empty cart", login="octo-bot")

        # Act
        document = event.to_document()

        # Assert
        self.assertEqual(document, {"project": "shop", "title": "Empty cart", "login": "octo-bot"})
