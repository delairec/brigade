import unittest

from brigade.commands.render_run_text import render_run_text


class RenderRunTextTest(unittest.TestCase):
    def test_should_count_the_segments_of_a_run_handed_over(self):
        # Arrange
        document = {
            "run": "20261007T090000Z-b70a01",
            "procedure": "deliver",
            "role": "builder",
            "slot": "build",
            "outcome": "done",
            "segments": 2,
        }

        # Act
        text = render_run_text(document)

        # Assert
        self.assertEqual(text, "run 20261007T090000Z-b70a01: deliver as builder (build) done after 2 segments")
