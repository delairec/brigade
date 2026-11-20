import unittest

from brigade.dashboard.render_rail import RailDocuments, render_rail

TWO_OPEN_WAVES = [{"wave": "oak_w1"}, {"wave": "oak_w2"}]
ONE_LIVE_RUN = [{"run": "20261118T101500Z-a1b2c3"}]
THREE_PATTERNS = [{"name": "a"}, {"name": "b"}, {"name": "c"}]
TWO_REPORTS = [{"id": "oak_w1"}, {"id": "oak_M1"}]


class RenderRailTest(unittest.TestCase):
    def test_should_group_the_views_and_count_beside_each_what_it_holds(self):
        # Arrange
        documents = RailDocuments(
            status={"waves": TWO_OPEN_WAVES, "live_runs": ONE_LIVE_RUN},
            inbox={"patterns": THREE_PATTERNS},
            reports={"reports": TWO_REPORTS},
        )

        # Act
        rendered = render_rail(documents)

        # Assert
        self.assertEqual(
            rendered,
            '<section class="rail-group"><h2>Operate</h2><a href="#status">Home</a>'
            '<a href="#waves">Waves <span class="count num">2 open</span></a>'
            '<a href="#runs">Runs <span class="count num">1 live</span></a>'
            '<a href="#inbox">Inbox <span class="count hot num">3</span></a></section>'
            '<section class="rail-group"><h2>Understand</h2><a href="#ledger">Ledger</a>'
            '<a href="#reports">Reports <span class="count num">2</span></a></section>',
        )

    def test_should_not_mark_the_inbox_hot_when_no_pattern_waits(self):
        # Arrange
        no_pattern = []
        documents = RailDocuments(
            status={"waves": [], "live_runs": []}, inbox={"patterns": no_pattern}, reports={"reports": []}
        )

        # Act
        rendered = render_rail(documents)

        # Assert
        self.assertIn('<a href="#inbox">Inbox <span class="count num">0</span></a>', rendered)
