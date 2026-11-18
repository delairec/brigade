import unittest

from brigade.dashboard.render_empty_state import render_empty_state


class RenderEmptyStateTest(unittest.TestCase):
    def test_should_say_why_it_is_empty_and_what_would_fill_it_escaped(self):
        # Act
        rendered = render_empty_state("No wave <yet>", "a wave opens once a task is todo & ratified")

        # Assert
        self.assertEqual(
            rendered,
            '<div class="empty-state"><p class="empty-why">No wave &lt;yet&gt;</p>'
            '<p class="empty-fill">a wave opens once a task is todo &amp; ratified</p></div>',
        )
