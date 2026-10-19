import unittest

from brigade.ledger.task_preflighted import TaskPreflighted

PASSING_ANCESTRY = {"name": "ancestry", "verdict": "pass", "findings": []}


class TaskPreflightedTest(unittest.TestCase):
    def test_should_read_the_findings_of_the_preflight_of_a_pull_request(self):
        # Act
        event = TaskPreflighted.from_document(
            {
                "event": "task.preflighted",
                "project": "shop",
                "wave": "shop_w1",
                "task": "S3",
                "pr": 42,
                "head": "0123abc",
                "checks": [PASSING_ANCESTRY],
            }
        )

        # Assert
        self.assertEqual(
            event,
            TaskPreflighted(
                project="shop", wave="shop_w1", task="S3", pr=42, head="0123abc", checks=(PASSING_ANCESTRY,)
            ),
        )

    def test_should_write_the_project_the_wave_the_task_the_pull_request_its_head_and_the_checks(self):
        # Arrange
        event = TaskPreflighted(
            project="shop", wave="shop_w1", task="S3", pr=42, head="0123abc", checks=(PASSING_ANCESTRY,)
        )

        # Act
        document = event.to_document()

        # Assert
        self.assertEqual(
            document,
            {
                "project": "shop",
                "wave": "shop_w1",
                "task": "S3",
                "pr": 42,
                "head": "0123abc",
                "checks": [{"name": "ancestry", "verdict": "pass", "findings": []}],
            },
        )
