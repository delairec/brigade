import unittest

from brigade.review.validate_answers import validate_answers
from brigade.system.validate_document import DocumentInvalid

FINDINGS = [{"id": "1", "grade": "high"}, {"id": "2", "grade": "low"}]


class ValidateAnswersTest(unittest.TestCase):
    def test_should_accept_one_answer_per_finding_of_the_context(self):
        # Arrange
        answers = {"answers": [{"finding": "2", "answer": "challenged"}, {"finding": "1", "answer": "fixed"}]}

        # Act
        refusal = validate_answers(answers, FINDINGS)

        # Assert
        self.assertIsNone(refusal)

    def test_should_refuse_a_document_lacking_the_answers(self):
        # Arrange
        no_answers = {}

        # Act
        with self.assertRaises(DocumentInvalid) as refusal:
            validate_answers(no_answers, FINDINGS)

        # Assert
        self.assertEqual(str(refusal.exception), "lacks the key answers")

    def test_should_refuse_answers_leaving_a_finding_unanswered(self):
        # Arrange
        answers = {"answers": [{"finding": "1", "answer": "fixed"}]}

        # Act
        with self.assertRaises(DocumentInvalid) as refusal:
            validate_answers(answers, FINDINGS)

        # Assert
        self.assertEqual(str(refusal.exception), "finding 2 has no answer")

    def test_should_refuse_an_answer_to_a_finding_the_context_does_not_hold(self):
        # Arrange
        answers = {
            "answers": [
                {"finding": "1", "answer": "fixed"},
                {"finding": "2", "answer": "fixed"},
                {"finding": "9", "answer": "fixed"},
            ]
        }

        # Act
        with self.assertRaises(DocumentInvalid) as refusal:
            validate_answers(answers, FINDINGS)

        # Assert
        self.assertEqual(str(refusal.exception), "finding 9 is no finding of the context")

    def test_should_refuse_a_finding_answered_twice(self):
        # Arrange
        answers = {
            "answers": [
                {"finding": "1", "answer": "fixed"},
                {"finding": "1", "answer": "challenged"},
                {"finding": "2", "answer": "fixed"},
            ]
        }

        # Act
        with self.assertRaises(DocumentInvalid) as refusal:
            validate_answers(answers, FINDINGS)

        # Assert
        self.assertEqual(str(refusal.exception), "finding 1 is answered twice")
