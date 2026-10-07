import unittest

from brigade.commands.render_runs_list_text import render_runs_list_text


class RenderRunsListTextTest(unittest.TestCase):
    def test_should_print_no_runs_when_the_list_is_empty(self):
        # Arrange
        document = {"runs": []}

        # Act
        text = render_runs_list_text(document)

        # Assert
        self.assertEqual(text, "no runs")

    def test_should_render_a_run_with_all_columns(self):
        # Arrange
        document = {
            "runs": [
                {
                    "run": "20261007T120000Z-abcdef",
                    "procedure": "review",
                    "slot": "bastien",
                    "role": "bastien",
                    "project": "tidepool",
                    "state": "finished",
                    "outcome": "done",
                }
            ]
        }

        # Act
        text = render_runs_list_text(document)

        # Assert
        self.assertEqual(text, "20261007T120000Z-abcdef  review  bastien  bastien  tidepool  finished  done")

    def test_should_render_an_absent_value_as_a_dash(self):
        # Arrange
        document = {
            "runs": [
                {
                    "run": "20261007T120000Z-abcdef",
                    "procedure": "review",
                    "slot": "bastien",
                    "role": "bastien",
                    "project": None,
                    "state": "dead",
                    "outcome": None,
                }
            ]
        }

        # Act
        text = render_runs_list_text(document)

        # Assert
        self.assertEqual(text, "20261007T120000Z-abcdef  review  bastien  bastien  -  dead  -")
