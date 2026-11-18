import unittest

from brigade.dashboard.render_svg_bar import SvgBar, render_svg_bar


class RenderSvgBarTest(unittest.TestCase):
    def test_should_fill_the_share_of_the_value_in_the_tone_of_its_state(self):
        # Arrange
        bar = SvgBar(label="turns <of B7>", state="running", value=30, total=120)

        # Act
        rendered = render_svg_bar(bar)

        # Assert
        self.assertEqual(
            rendered,
            '<svg class="bar" viewBox="0 0 100 8" role="img" aria-label="turns &lt;of B7&gt;">'
            '<rect class="bar-track" width="100" height="8"></rect>'
            '<rect class="bar-fill tone-work" width="25" height="8"></rect></svg>',
        )

    def test_should_bound_the_fill_to_the_track(self):
        # Arrange
        rows = [("no total", 5, 0, "0"), ("a value past its total", 150, 120, "100")]
        for case, value, total, width in rows:
            with self.subTest(case=case):
                bar = SvgBar(label="turns", state="turn_limit", value=value, total=total)

                # Act
                rendered = render_svg_bar(bar)

                # Assert
                self.assertEqual(
                    rendered,
                    '<svg class="bar" viewBox="0 0 100 8" role="img" aria-label="turns">'
                    '<rect class="bar-track" width="100" height="8"></rect>'
                    f'<rect class="bar-fill tone-limit" width="{width}" height="8"></rect></svg>',
                )
