import unittest

from brigade.ledger.task_promoted import TaskPromoted


class TaskPromotedTest(unittest.TestCase):
    def test_should_read_the_promotion_of_a_task(self):
        # Act
        event = TaskPromoted.from_document(
            {"event": "task.promoted", "project": "shop", "task": "S3", "pr": 12, "commit": "4b825dc6"}
        )

        # Assert
        self.assertEqual(event, TaskPromoted(project="shop", task="S3", pr=12, commit="4b825dc6"))

    def test_should_write_the_project_the_task_the_pull_request_and_the_commit(self):
        # Arrange
        event = TaskPromoted(project="shop", task="S3", pr=12, commit="4b825dc6")

        # Act
        document = event.to_document()

        # Assert
        self.assertEqual(document, {"project": "shop", "task": "S3", "pr": 12, "commit": "4b825dc6"})
