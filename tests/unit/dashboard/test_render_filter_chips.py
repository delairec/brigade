import unittest

from brigade.dashboard.render_filter_chips import FilterChip, render_filter_chips


class RenderFilterChipsTest(unittest.TestCase):
    def test_should_link_each_filter_and_mark_the_chosen_one_escaped(self):
        # Arrange
        chips = [
            FilterChip(label="All <waves>", view="waves", chosen=True),
            FilterChip(label="parked", view='waves?state=parked&x="', chosen=False),
        ]

        # Act
        rendered = render_filter_chips(chips)

        # Assert
        self.assertEqual(
            rendered,
            '<nav class="chips"><a class="chip" href="#waves" aria-current="true">All &lt;waves&gt;</a>'
            '<a class="chip" href="#waves?state=parked&amp;x=&quot;">parked</a></nav>',
        )
