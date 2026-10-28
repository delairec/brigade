import unittest

from brigade.dashboard.render_action import render_action


class RenderActionTest(unittest.TestCase):
    def test_should_render_a_button_posting_to_the_route_of_the_action(self):
        # Act
        button = render_action(("waves", "w4", "tasks", "B28", "requeue"), "requeue")

        # Assert
        self.assertEqual(button, ' <button type="button" data-post="/api/waves/w4/tasks/B28/requeue">requeue</button>')

    def test_should_quote_each_segment_of_the_route(self):
        # Act
        button = render_action(("projects", 'a/b"<c>', "pause"), "pause")

        # Assert
        self.assertEqual(
            button, ' <button type="button" data-post="/api/projects/a%2Fb%22%3Cc%3E/pause">pause</button>'
        )
