import unittest

from brigade.commands.render_run_text import render_run_text


class RenderRunTextTest(unittest.TestCase):
    def test_should_print_the_run_id_when_the_document_has_no_outcome(self):
        # Arrange
        document = {"run": "20261007T120000Z-abcdef"}

        # Act
        text = render_run_text(document)

        # Assert
        self.assertEqual(text, "20261007T120000Z-abcdef")

    def test_should_name_a_single_segment_in_the_singular(self):
        # Arrange
        document = {
            "run": "20261007T120000Z-abcdef",
            "procedure": "review",
            "role": "bastien",
            "slot": "bastien",
            "outcome": "done",
            "segments": 1,
        }

        # Act
        text = render_run_text(document)

        # Assert
        self.assertEqual(text, "run 20261007T120000Z-abcdef: review as bastien (bastien) done after 1 segment")

    def test_should_name_several_segments_in_the_plural(self):
        # Arrange
        document = {
            "run": "20261007T120000Z-abcdef",
            "procedure": "review",
            "role": "bastien",
            "slot": "bastien",
            "outcome": "done",
            "segments": 3,
        }

        # Act
        text = render_run_text(document)

        # Assert
        self.assertEqual(text, "run 20261007T120000Z-abcdef: review as bastien (bastien) done after 3 segments")
