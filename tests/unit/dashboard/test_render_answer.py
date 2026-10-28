import unittest

from brigade.dashboard.render_answer import render_answer
from brigade.dashboard.run_routed_command import CommandAnswer


def render_count(document: dict) -> str:
    return f"<p>{document['count']}</p>"


class RenderAnswerTest(unittest.TestCase):
    def test_should_render_the_document_of_a_command_that_succeeded(self):
        # Arrange
        answer = CommandAnswer(status=200, document='{"count": 3}')

        # Act
        fragment = render_answer(answer, render_count)

        # Assert
        self.assertEqual(fragment, "<p>3</p>")

    def test_should_render_the_escaped_error_of_a_command_that_failed(self):
        # Arrange
        answer = CommandAnswer(status=500, document='{"error": "<b>boom</b>"}')

        # Act
        fragment = render_answer(answer, render_count)

        # Assert
        self.assertEqual(fragment, "<dl><dt>error</dt><dd>&lt;b&gt;boom&lt;/b&gt;</dd></dl>")
