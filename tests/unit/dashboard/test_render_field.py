import unittest

from brigade.dashboard.render_field import render_field


class RenderFieldTest(unittest.TestCase):
    def test_should_label_a_control_beside_it(self):
        # Arrange
        control = '<select id="runs-wave" name="wave"><option>any</option></select>'

        # Act
        rendered = render_field("Wave <of>", "runs-wave", control)

        # Assert
        self.assertEqual(
            rendered,
            '<span class="field"><label for="runs-wave">Wave &lt;of&gt;</label>'
            '<select id="runs-wave" name="wave"><option>any</option></select></span>',
        )
