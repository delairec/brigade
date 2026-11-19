import unittest

from brigade.dashboard.render_awawa_dot import render_awawa_dot


class RenderAwawaDotTest(unittest.TestCase):
    def test_should_dot_a_status_in_its_tone_and_name_it(self):
        # Arrange
        rows = [
            ("a status", "implemented", '<span class="dot tone-done" title="implemented"></span>'),
            ("no status", None, '<span class="dot tone-faint" title="no status"></span>'),
            ("a status holding markup", "<b>", '<span class="dot tone-faint" title="&lt;b&gt;"></span>'),
        ]
        for case, status, dot in rows:
            with self.subTest(case):
                # Act
                rendered = render_awawa_dot(status)

                # Assert
                self.assertEqual(rendered, dot)
