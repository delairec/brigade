import io
import unittest

from brigade.dashboard.answer_addon_lines import answer_addon_lines


def answer_with_the_project(message: dict) -> dict:
    return {"document": {"project": message["project"]}}


class AnswerAddonLinesTest(unittest.TestCase):
    def test_should_answer_each_request_line_with_one_line(self):
        # Arrange
        reader = io.StringIO('{"project": "app"}\n{"project": "shop"}\n')
        writer = io.StringIO()

        # Act
        answered = answer_addon_lines(reader, writer, answer_with_the_project)

        # Assert
        self.assertEqual(answered, 2)
        self.assertEqual(writer.getvalue(), '{"document": {"project": "app"}}\n{"document": {"project": "shop"}}\n')

    def test_should_answer_a_line_that_is_not_json_with_an_error(self):
        # Arrange
        reader = io.StringIO("board\n")
        writer = io.StringIO()

        # Act
        answer_addon_lines(reader, writer, answer_with_the_project)

        # Assert
        self.assertEqual(
            writer.getvalue(),
            '{"error": "the request is not JSON: Expecting value: line 1 column 1 (char 0)"}\n',
        )
