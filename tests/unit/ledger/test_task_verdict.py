import unittest

from brigade.ledger.task_verdict import TaskVerdict

BROKEN_SPEC = {"grade": "high", "file": "src/tides.py", "line": 12, "broken": "SPEC 2 of @TASK.T7"}


class TaskVerdictTest(unittest.TestCase):
    def test_should_read_the_verdict_on_the_head_of_a_pull_request(self):
        # Act
        event = TaskVerdict.from_document(
            {
                "event": "task.verdict",
                "project": "tidepool",
                "wave": "tidepool_w16",
                "task": "T7",
                "pr": 42,
                "head": "8885daa",
                "verdict": "changes",
                "findings": [BROKEN_SPEC],
                "login": "tidepool-review",
            }
        )

        # Assert
        self.assertEqual(
            event,
            TaskVerdict(
                project="tidepool",
                wave="tidepool_w16",
                task="T7",
                pr=42,
                head="8885daa",
                verdict="changes",
                findings=(BROKEN_SPEC,),
                login="tidepool-review",
            ),
        )

    def test_should_write_the_verdict_its_findings_and_the_login_of_the_review(self):
        # Arrange
        no_review_posted = None
        event = TaskVerdict(
            project="tidepool",
            wave="tidepool_w16",
            task="T7",
            pr=42,
            head="8885daa",
            verdict="pass",
            findings=(BROKEN_SPEC,),
            login=no_review_posted,
        )

        # Act
        document = event.to_document()

        # Assert
        self.assertEqual(
            document,
            {
                "project": "tidepool",
                "wave": "tidepool_w16",
                "task": "T7",
                "pr": 42,
                "head": "8885daa",
                "verdict": "pass",
                "findings": [{"grade": "high", "file": "src/tides.py", "line": 12, "broken": "SPEC 2 of @TASK.T7"}],
                "login": None,
            },
        )
