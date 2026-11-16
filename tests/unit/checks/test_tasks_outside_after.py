import unittest

from brigade.checks.tasks_outside_after import check
from tests.unit.create_test_runtime import create_test_runtime


def create_subject(after: list, items: list) -> dict:
    return {
        "schema_version": 1,
        "project": "/srv/shop",
        "parameters": {"task": "B9"},
        "collected": {
            "draft": {
                "summary": {
                    "task": "B9",
                    "after": after,
                    "source_commit": "2222222222222222222222222222222222222222",
                    "files": ["brigade/cart.py", "brigade/till.py"],
                    "entities": [],
                    "citations": [],
                },
                "items": items,
            }
        },
    }


class TasksOutsideAfterCheckTest(unittest.TestCase):
    def test_should_report_a_task_on_a_file_of_the_draft_that_its_after_does_not_name(self):
        # Arrange
        subject = create_subject(
            ["B3"],
            [
                {"task": "B3", "status": "todo", "files": ["brigade/till.py"], "entities": []},
                {"task": "B4", "status": "draft", "files": ["brigade/till.py", "brigade/shelf.py"], "entities": []},
            ],
        )

        # Act
        document = check(subject, create_test_runtime())

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "name": "tasks_outside_after",
                "result": "fail",
                "findings": ["@TASK.B4 (draft) touches brigade/till.py, outside the AFTER of @TASK.B9"],
            },
        )

    def test_should_pass_a_draft_whose_after_names_every_task_on_its_files(self):
        # Arrange
        subject = create_subject(
            ["B3"],
            [
                {"task": "B3", "status": "todo", "files": ["brigade/till.py"], "entities": []},
                {"task": "B5", "status": "todo", "files": ["brigade/shelf.py"], "entities": []},
            ],
        )

        # Act
        document = check(subject, create_test_runtime())

        # Assert
        self.assertEqual(
            document, {"schema_version": 1, "name": "tasks_outside_after", "result": "ok", "findings": []}
        )
