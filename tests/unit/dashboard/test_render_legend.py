import unittest

from brigade.dashboard.render_legend import LegendItem, render_legend


class RenderLegendTest(unittest.TestCase):
    def test_should_name_each_tone_a_chart_draws_the_softer_ones_marked_soft(self):
        # Arrange
        items = (
            LegendItem(label="building", state="running"),
            LegendItem(label="fixing <or> rebasing", state="fixing", soft=True),
        )

        # Act
        rendered = render_legend(items)

        # Assert
        self.assertEqual(
            rendered,
            '<figcaption class="legend"><span class="tone-work">building</span>'
            '<span class="tone-work soft">fixing &lt;or&gt; rebasing</span></figcaption>',
        )
