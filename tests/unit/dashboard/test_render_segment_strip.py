import unittest

from brigade.dashboard.render_segment_strip import Segment, render_segment_strip


class RenderSegmentStripTest(unittest.TestCase):
    def test_should_lay_each_segment_by_its_share_in_the_tone_of_its_end(self):
        # Arrange
        segments = [
            Segment(label="s1 <a>", state="handed_over", length=30),
            Segment(label="s2", state="done", length=10),
        ]

        # Act
        rendered = render_segment_strip("segments <of the run>", segments)

        # Assert
        self.assertEqual(
            rendered,
            '<svg class="segment-strip" viewBox="0 0 100 8" role="img" aria-label="segments &lt;of the run&gt;">'
            '<rect class="segment tone-faint" x="0" width="75" height="8"><title>s1 &lt;a&gt;</title></rect>'
            '<rect class="segment tone-done" x="75" width="25" height="8"><title>s2</title></rect></svg>',
        )

    def test_should_draw_an_empty_strip_without_segments(self):
        # Arrange
        no_segment = []

        # Act
        rendered = render_segment_strip("segments", no_segment)

        # Assert
        self.assertEqual(
            rendered, '<svg class="segment-strip" viewBox="0 0 100 8" role="img" aria-label="segments"></svg>'
        )
