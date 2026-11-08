import io
import unittest

from brigade.system.ask_on_terminal import ask_on_terminal


class _TerminalDouble(io.StringIO):
    def isatty(self) -> bool:
        return True


class AskOnTerminalTest(unittest.TestCase):
    def test_should_print_the_question_and_answer_the_line_typed(self):
        # Arrange
        answering = _TerminalDouble("area\n")
        prompting = io.StringIO()

        # Act
        answer = ask_on_terminal(answering, prompting, "Corpus mode: ")

        # Assert
        self.assertEqual(answer, "area")
        self.assertEqual(prompting.getvalue(), "Corpus mode: ")

    def test_should_answer_nothing_when_stdin_is_no_terminal(self):
        # Arrange
        piped_stdin = io.StringIO("area\n")
        prompting = io.StringIO()

        # Act
        answer = ask_on_terminal(piped_stdin, prompting, "Corpus mode: ")

        # Assert
        self.assertIsNone(answer)
        self.assertEqual(prompting.getvalue(), "")

    def test_should_answer_nothing_when_stdin_is_closed(self):
        # Arrange
        closed_stdin = None
        prompting = io.StringIO()

        # Act
        answer = ask_on_terminal(closed_stdin, prompting, "Corpus mode: ")

        # Assert
        self.assertIsNone(answer)
