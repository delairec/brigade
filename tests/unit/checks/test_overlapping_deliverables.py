import unittest

from brigade.checks.overlapping_deliverables import check
from tests.unit.create_test_runtime import create_test_runtime


def create_subject(items: list) -> dict:
    return {
        "schema_version": 1,
        "project": "/srv/shop",
        "parameters": {"task": "B9"},
        "collected": {
            "draft": {
                "summary": {
                    "task": "B9",
                    "after": ["B3"],
                    "source_commit": "2222222222222222222222222222222222222222",
                    "files": ["brigade/cart.py", "brigade/till.py"],
                    "entities": ["@DECISION.ReceiptsAreKept"],
                    "citations": [],
                },
                "items": items,
            }
        },
    }


class OverlappingDeliverablesCheckTest(unittest.TestCase):
    def test_should_report_each_task_with_the_files_and_the_entities_it_cites_in_common(self):
        # Arrange
        subject = create_subject(
            [
                {
                    "task": "B3",
                    "status": "todo",
                    "files": ["brigade/till.py"],
                    "entities": ["@DECISION.ReceiptsAreKept"],
                },
                {
                    "task": "B4",
                    "status": "draft",
                    "files": ["brigade/till.py", "brigade/shelf.py"],
                    "entities": ["@DECISION.ReceiptsAreKept", "@DECISION.ShelvesAreCounted"],
                },
            ]
        )

        # Act
        document = check(subject, create_test_runtime())

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "name": "overlapping_deliverables",
                "verdict": "fail",
                "findings": [
                    "@TASK.B3 (todo) cites brigade/till.py, @DECISION.ReceiptsAreKept as @TASK.B9 does",
                    "@TASK.B4 (draft) cites brigade/till.py, @DECISION.ReceiptsAreKept as @TASK.B9 does",
                ],
            },
        )

    def test_should_pass_a_draft_whose_deliverables_no_task_shares(self):
        # Arrange
        subject = create_subject(
            [
                {
                    "task": "B5",
                    "status": "todo",
                    "files": ["brigade/shelf.py"],
                    "entities": ["@DECISION.ShelvesAreCounted"],
                }
            ]
        )

        # Act
        document = check(subject, create_test_runtime())

        # Assert
        self.assertEqual(
            document, {"schema_version": 1, "name": "overlapping_deliverables", "verdict": "pass", "findings": []}
        )
