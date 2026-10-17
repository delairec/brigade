import unittest

from brigade.ledger.task_pr_opened import TaskPrOpened


class TaskPrOpenedTest(unittest.TestCase):
    def test_should_read_the_pull_request_opened_for_a_task(self):
        # Act
        event = TaskPrOpened.from_document(
            {
                "event": "task.pr_opened",
                "project": "shop",
                "task": "S3",
                "wave": "M1",
                "branch": "task/M1-empty-cart/S3",
                "pr": 12,
                "login": "octo-bot",
            }
        )

        # Assert
        self.assertEqual(
            event,
            TaskPrOpened(project="shop", task="S3", wave="M1", branch="task/M1-empty-cart/S3", pr=12, login="octo-bot"),
        )

    def test_should_write_the_project_the_task_the_wave_the_branch_the_pull_request_and_the_login(self):
        # Arrange
        event = TaskPrOpened(
            project="shop", task="S3", wave="M1", branch="task/M1-empty-cart/S3", pr=12, login="octo-bot"
        )

        # Act
        document = event.to_document()

        # Assert
        self.assertEqual(
            document,
            {
                "project": "shop",
                "task": "S3",
                "wave": "M1",
                "branch": "task/M1-empty-cart/S3",
                "pr": 12,
                "login": "octo-bot",
            },
        )
