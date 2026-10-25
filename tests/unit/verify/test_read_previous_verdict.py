import unittest

from brigade.ledger.task_review_answered import TaskReviewAnswered
from brigade.ledger.task_verdict import TaskVerdict
from brigade.verify.read_previous_verdict import VerifiedPullRequest, read_previous_verdict

VERIFIED = VerifiedPullRequest(project="tidepool", task="T7", pr=42)
TIDE_TABLE_READ_TWICE = {
    "grade": "high",
    "file": "src/tides.py",
    "line": 12,
    "broken": "SPEC 2 of @TASK.T7",
    "summary": "the tide table is read twice",
}
UNTESTED_EBB = {
    "grade": "low",
    "file": "src/ebb.py",
    "line": 3,
    "broken": "@RULE.test_first_properties",
    "summary": "the ebb has no test",
}


def create_verdict(head: str, findings: tuple[dict, ...], **changed) -> TaskVerdict:
    fields = {
        "project": "tidepool",
        "wave": "tidepool_w16",
        "task": "T7",
        "pr": 42,
        "head": head,
        "verdict": "changes",
        "findings": findings,
        "login": None,
    }
    return TaskVerdict(**{**fields, **changed})


def create_answers(head: str, answers: tuple[dict, ...], **changed) -> TaskReviewAnswered:
    fields = {
        "project": "tidepool",
        "wave": "tidepool_w16",
        "task": "T7",
        "pr": 42,
        "head": head,
        "answers": answers,
        "login": None,
    }
    return TaskReviewAnswered(**{**fields, **changed})


class ReadPreviousVerdictTest(unittest.TestCase):
    def test_should_find_no_previous_verdict_when_none_of_the_task_is_recorded(self):
        # Arrange
        verdict_of_another_task = create_verdict("8885daa", (TIDE_TABLE_READ_TWICE,), task="T8", pr=43)

        # Act
        previous = read_previous_verdict([verdict_of_another_task], VERIFIED)

        # Assert
        self.assertIsNone(previous)

    def test_should_give_the_last_verdict_with_each_finding_by_its_identifier_and_its_answer(self):
        # Arrange
        events = [
            create_verdict("69038bd", (TIDE_TABLE_READ_TWICE, UNTESTED_EBB)),
            create_answers(
                "69038bd",
                (
                    {"finding": "1", "answer": "the table is cached"},
                    {"finding": "2", "answer": "the ebb test is added"},
                ),
            ),
            create_verdict("efd5ed1", (TIDE_TABLE_READ_TWICE, UNTESTED_EBB)),
            create_answers("efd5ed1", ({"finding": "1", "answer": "fixed by 51dee9a: the table is read once"},)),
        ]

        # Act
        previous = read_previous_verdict(events, VERIFIED)

        # Assert
        self.assertEqual(
            previous,
            {
                "head": "efd5ed1",
                "verdict": "changes",
                "findings": [
                    {
                        "id": "1",
                        "grade": "high",
                        "file": "src/tides.py",
                        "line": 12,
                        "broken": "SPEC 2 of @TASK.T7",
                        "summary": "the tide table is read twice",
                        "answer": "fixed by 51dee9a: the table is read once",
                    },
                    {
                        "id": "2",
                        "grade": "low",
                        "file": "src/ebb.py",
                        "line": 3,
                        "broken": "@RULE.test_first_properties",
                        "summary": "the ebb has no test",
                        "answer": None,
                    },
                ],
            },
        )

    def test_should_give_the_answer_of_the_last_answers_recorded_for_a_finding(self):
        # Arrange
        events = [
            create_verdict("efd5ed1", (TIDE_TABLE_READ_TWICE,)),
            create_answers("efd5ed1", ({"finding": "1", "answer": "the table is read once"},)),
            create_answers("51dee9a", ({"finding": "1", "answer": "challenged: the second read is the cache"},)),
        ]

        # Act
        previous = read_previous_verdict(events, VERIFIED)

        # Assert
        self.assertEqual(previous["findings"][0]["answer"], "challenged: the second read is the cache")

    def test_should_ignore_the_answers_of_another_task(self):
        # Arrange
        events = [
            create_verdict("efd5ed1", (TIDE_TABLE_READ_TWICE,)),
            create_answers("a1b2c3d", ({"finding": "1", "answer": "the table is read once"},), task="T8", pr=43),
        ]

        # Act
        previous = read_previous_verdict(events, VERIFIED)

        # Assert
        self.assertIsNone(previous["findings"][0]["answer"])

    def test_should_give_no_summary_for_a_finding_recorded_without_one(self):
        # Arrange
        recorded_without_summary = {"grade": "low", "file": "src/ebb.py", "line": 3, "broken": "@RULE.kiss"}

        # Act
        previous = read_previous_verdict([create_verdict("efd5ed1", (recorded_without_summary,))], VERIFIED)

        # Assert
        self.assertIsNone(previous["findings"][0]["summary"])
