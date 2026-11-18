import unittest

from brigade.dashboard.render_status_pill import render_status_pill


class RenderStatusPillTest(unittest.TestCase):
    def test_should_frame_the_tone_of_the_state(self):
        # Act
        pill = render_status_pill("verifying")

        # Assert
        self.assertEqual(
            pill,
            '<span class="pill"><span class="tone tone-review"><span class="tone-shape" aria-hidden="true">◆</span>'
            "verifying</span></span>",
        )

    def test_should_escape_a_state_holding_markup(self):
        # Act
        pill = render_status_pill('"><script>')

        # Assert
        self.assertEqual(
            pill,
            '<span class="pill"><span class="tone tone-faint"><span class="tone-shape" aria-hidden="true">·</span>'
            "&quot;&gt;&lt;script&gt;</span></span>",
        )
