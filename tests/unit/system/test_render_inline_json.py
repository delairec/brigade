import unittest

from brigade.system.render_inline_json import render_inline_json


class RenderInlineJsonTest(unittest.TestCase):
    def test_should_render_the_value_as_json_on_one_line(self):
        # Arrange
        summary = {"open": 3, "labels": ["bug", "ci"]}

        # Act
        text = render_inline_json(summary)

        # Assert
        self.assertEqual(text, '{"open": 3, "labels": ["bug", "ci"]}')
