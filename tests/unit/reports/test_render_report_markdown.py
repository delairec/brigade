import unittest

from brigade.reports.render_report_markdown import render_report_markdown


class RenderReportMarkdownTest(unittest.TestCase):
    def test_should_render_the_manual_tests_and_the_tester_steps_as_tables(self):
        # Arrange
        entity = {
            "type": "REPORT",
            "name": "oak_w3",
            "fields": [
                {"name": "WAVE", "value": "oak_w3"},
                {"name": "MANUAL_TEST", "value": "OK1: the page lists the waves"},
                {"name": "MANUAL_TEST", "value": "OK2: a | in a title stays in its cell"},
                {"name": "TESTER_STEP", "value": "open the page and read the waves"},
                {"name": "NARRATIVE", "value": "the wave merged both tasks"},
            ],
        }

        # Act
        markdown = render_report_markdown(entity)

        # Assert
        self.assertEqual(
            markdown,
            "# REPORT oak_w3\n\n"
            "- WAVE: oak_w3\n"
            "- NARRATIVE: the wave merged both tasks\n"
            "\n## Manual tests\n\n"
            "| # | test |\n"
            "| --- | --- |\n"
            "| 1 | OK1: the page lists the waves |\n"
            "| 2 | OK2: a \\| in a title stays in its cell |\n"
            "\n## Tester steps\n\n"
            "| # | test |\n"
            "| --- | --- |\n"
            "| 1 | open the page and read the waves |\n",
        )

    def test_should_render_an_answer_without_manual_tests_as_its_fields(self):
        # Arrange
        entity = {"type": "ANSWER", "name": "health_r1", "fields": [{"name": "STUDY", "value": "health"}]}

        # Act
        markdown = render_report_markdown(entity)

        # Assert
        self.assertEqual(markdown, "# ANSWER health_r1\n\n- STUDY: health\n")
