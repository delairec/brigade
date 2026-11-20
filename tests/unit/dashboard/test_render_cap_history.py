import unittest

from brigade.dashboard.render_cap_history import render_cap_history


class RenderCapHistoryTest(unittest.TestCase):
    def test_should_step_up_to_a_raised_cap_and_mark_the_change(self):
        # Arrange
        budget = {
            "applied": 90,
            "history": [{"ts": "2026-11-02T08:30:00Z", "before": 60, "after": 90, "direction": "raised"}],
            "stable": False,
        }

        # Act
        rendered = render_cap_history("ada", budget)

        # Assert
        self.assertEqual(
            rendered,
            '<svg class="cap-history" viewBox="0 0 400 78" role="img" aria-label="turn cap of ada">'
            '<text class="cap-role" x="0" y="12">ada</text>'
            '<path class="step-path tone-work" d="M0 33.3333 H200 V20 H400"></path>'
            '<circle class="cap-change tone-limit" cx="200" cy="20" r="3"></circle>'
            '<text class="cap-label" x="0" y="74">raised at 2026-11-02T08:30:00Z: 60 to 90</text>'
            "</svg>",
        )

    def test_should_step_down_through_each_lowered_cap_and_mark_each_change(self):
        # Arrange
        budget = {
            "applied": 40,
            "history": [
                {"ts": "2026-11-02T08:30:00Z", "before": 80, "after": 60, "direction": "lowered"},
                {"ts": "2026-11-04T17:05:00Z", "before": 60, "after": 40, "direction": "lowered"},
            ],
            "stable": False,
        }

        # Act
        rendered = render_cap_history("remi", budget)

        # Assert
        self.assertEqual(
            rendered,
            '<svg class="cap-history" viewBox="0 0 400 92" role="img" aria-label="turn cap of remi">'
            '<text class="cap-role" x="0" y="12">remi</text>'
            '<path class="step-path tone-work" d="M0 20 H133.333 V30 H266.667 V40 H400"></path>'
            '<circle class="cap-change tone-done" cx="133.333" cy="30" r="3"></circle>'
            '<circle class="cap-change tone-done" cx="266.667" cy="40" r="3"></circle>'
            '<text class="cap-label" x="0" y="74">lowered at 2026-11-02T08:30:00Z: 80 to 60</text>'
            '<text class="cap-label" x="0" y="88">lowered at 2026-11-04T17:05:00Z: 60 to 40</text>'
            "</svg>",
        )

    def test_should_draw_a_flat_line_at_the_applied_cap_marked_stable_for_a_role_with_no_change(self):
        # Arrange
        no_change = []
        budget = {"applied": 40, "history": no_change, "stable": True}

        # Act
        rendered = render_cap_history("prudence", budget)

        # Assert
        self.assertEqual(
            rendered,
            '<svg class="cap-history" viewBox="0 0 400 78" role="img" aria-label="turn cap of prudence">'
            '<text class="cap-role" x="0" y="12">prudence</text>'
            '<path class="step-path tone-work" d="M0 20 H400"></path>'
            '<text class="cap-label" x="0" y="74">stable at 40</text>'
            "</svg>",
        )

    def test_should_render_escaped_a_role_name_holding_markup(self):
        # Arrange
        no_change = []
        budget = {"applied": 40, "history": no_change, "stable": True}

        # Act
        rendered = render_cap_history('<b class="x">ada</b>', budget)

        # Assert
        self.assertEqual(
            rendered,
            '<svg class="cap-history" viewBox="0 0 400 78" role="img"'
            ' aria-label="turn cap of &lt;b class=&quot;x&quot;&gt;ada&lt;/b&gt;">'
            '<text class="cap-role" x="0" y="12">&lt;b class=&quot;x&quot;&gt;ada&lt;/b&gt;</text>'
            '<path class="step-path tone-work" d="M0 20 H400"></path>'
            '<text class="cap-label" x="0" y="74">stable at 40</text>'
            "</svg>",
        )

    def test_should_render_escaped_the_ts_of_a_change(self):
        # Arrange
        budget = {
            "applied": 90,
            "history": [{"ts": "<i>now</i>", "before": 60, "after": 90, "direction": "raised"}],
            "stable": False,
        }

        # Act
        rendered = render_cap_history("ada", budget)

        # Assert
        self.assertIn(
            '<text class="cap-label" x="0" y="74">raised at &lt;i&gt;now&lt;/i&gt;: 60 to 90</text>', rendered
        )
