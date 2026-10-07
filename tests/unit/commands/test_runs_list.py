import unittest

from brigade.commands.runs_list import COMMAND


class RunsListTextTest(unittest.TestCase):
    def test_should_say_that_no_run_was_started(self):
        # Arrange
        document = {"schema_version": 1, "runs": []}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "no runs")
