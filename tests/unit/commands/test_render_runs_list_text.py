import unittest

from brigade.commands.render_runs_list_text import render_runs_list_text


class RenderRunsListTextTest(unittest.TestCase):
    def test_should_say_that_no_run_was_started(self):
        # Arrange
        document = {"schema_version": 1, "runs": []}

        # Act
        text = render_runs_list_text(document)

        # Assert
        self.assertEqual(text, "no runs")
