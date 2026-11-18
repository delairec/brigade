import unittest

from brigade.dashboard.render_stat_tile import StatTile, render_stat_tile


class RenderStatTileTest(unittest.TestCase):
    def test_should_show_the_figure_with_what_it_covers_escaped(self):
        # Arrange
        tile = StatTile(label="cost <usd>", value="$4 & up", perimeter="3 runs <of 5> record a cost")

        # Act
        rendered = render_stat_tile(tile)

        # Assert
        self.assertEqual(
            rendered,
            '<div class="stat-tile"><span class="stat-value">$4 &amp; up</span>'
            '<span class="stat-label">cost &lt;usd&gt;</span>'
            '<span class="stat-perimeter">3 runs &lt;of 5&gt; record a cost</span></div>',
        )
