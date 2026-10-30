import unittest

from brigade.runs.read_run_question import read_run_question

NO_MESSAGE = None


class ReadRunQuestionTest(unittest.TestCase):
    def test_should_join_the_lines_above_the_end_line_of_the_run_into_its_question(self):
        # Arrange
        message = "Keep the guard of plan.py\n\n  or drop it?\nbrigade-end: blocked"

        # Act
        question = read_run_question(message)

        # Assert
        self.assertEqual(question, "Keep the guard of plan.py or drop it?")

    def test_should_read_no_question_from_a_run_that_left_no_message(self):
        # Act
        question = read_run_question(NO_MESSAGE)

        # Assert
        self.assertEqual(question, "")
