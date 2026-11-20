import unittest

from brigade.dashboard.render_segment_squares import render_segment_squares


class RenderSegmentSquaresTest(unittest.TestCase):
    def test_should_show_one_square_per_segment_in_the_tone_of_its_outcome_for_a_run_cut_then_done(self):
        # Act
        squares = render_segment_squares(["wall_limit", "done"])

        # Assert
        self.assertEqual(
            squares,
            '<span class="segment-squares" role="img" aria-label="segments: wall_limit, done">'
            '<span class="segment-square tone-limit" title="wall_limit"></span>'
            '<span class="segment-square tone-done" title="done"></span></span>',
        )

    def test_should_render_an_outcome_holding_markup_escaped(self):
        # Act
        squares = render_segment_squares(["<b>done</b>"])

        # Assert
        self.assertEqual(
            squares,
            '<span class="segment-squares" role="img" aria-label="segments: &lt;b&gt;done&lt;/b&gt;">'
            '<span class="segment-square tone-faint" title="&lt;b&gt;done&lt;/b&gt;"></span></span>',
        )
