import unittest

from brigade.dashboard.render_callout import render_callout


class RenderCalloutTest(unittest.TestCase):
    def test_should_frame_the_text_in_the_tone_of_its_state_escaped(self):
        # Act
        rendered = render_callout("parked", "B7 waits <for you>")

        # Assert
        self.assertEqual(rendered, '<div class="callout tone-you"><p>B7 waits &lt;for you&gt;</p></div>')
