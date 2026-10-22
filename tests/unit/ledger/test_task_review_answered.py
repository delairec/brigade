import unittest

from brigade.ledger.task_review_answered import TaskReviewAnswered


class TaskReviewAnsweredTest(unittest.TestCase):
    def test_should_read_the_answers_to_the_review_of_a_pull_request(self):
        # Act
        event = TaskReviewAnswered.from_document(
            {
                "event": "task.review_answered",
                "project": "tidepool",
                "wave": "tidepool_w16",
                "task": "T7",
                "pr": 42,
                "head": "8885daa",
                "answers": [{"finding": "1", "answer": "fixed by 8885daa"}],
                "login": "tidepool-remediate",
            }
        )

        # Assert
        self.assertEqual(
            event,
            TaskReviewAnswered(
                project="tidepool",
                wave="tidepool_w16",
                task="T7",
                pr=42,
                head="8885daa",
                answers=({"finding": "1", "answer": "fixed by 8885daa"},),
                login="tidepool-remediate",
            ),
        )
