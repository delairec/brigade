import unittest

from brigade.dashboard.render_nothing_matching import render_nothing_matching


class RenderNothingMatchingTest(unittest.TestCase):
    def test_should_say_that_no_entity_matches_and_how_to_see_the_whole_corpus(self):
        # Act
        rendered = render_nothing_matching()

        # Assert
        self.assertEqual(
            rendered,
            '<div class="empty-state"><p class="empty-why">No entity matches this address.</p>'
            '<p class="empty-fill">Clear the filters and the search to see the whole corpus.</p></div>',
        )
