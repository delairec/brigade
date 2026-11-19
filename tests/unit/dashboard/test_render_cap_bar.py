import unittest

from brigade.dashboard.render_cap_bar import CapBar, render_cap_bar


class RenderCapBarTest(unittest.TestCase):
    def test_should_mark_the_cap_on_a_track_as_long_as_the_value_past_it(self):
        # Arrange
        bar = CapBar(label="turns <of remi>", state="turn_limit", value=64, cap=50)

        # Act
        rendered = render_cap_bar(bar)

        # Assert
        self.assertEqual(
            rendered,
            '<svg class="bar" viewBox="0 0 100 8" role="img" aria-label="turns &lt;of remi&gt;">'
            '<rect class="bar-track" width="100" height="8"></rect>'
            '<rect class="bar-fill tone-limit" width="100" height="8"></rect>'
            '<line class="bar-cap" x1="78.125" y1="0" x2="78.125" y2="8"></line></svg>',
        )

    def test_should_end_the_track_on_the_cap_of_a_value_under_it(self):
        # Arrange
        bar = CapBar(label="turns of rebaser", state="done", value=12, cap=30)

        # Act
        rendered = render_cap_bar(bar)

        # Assert
        self.assertEqual(
            rendered,
            '<svg class="bar" viewBox="0 0 100 8" role="img" aria-label="turns of rebaser">'
            '<rect class="bar-track" width="100" height="8"></rect>'
            '<rect class="bar-fill tone-done" width="40" height="8"></rect>'
            '<line class="bar-cap" x1="100" y1="0" x2="100" y2="8"></line></svg>',
        )
