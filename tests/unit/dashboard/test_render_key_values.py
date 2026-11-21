import unittest

from brigade.dashboard.render_key_values import render_key_values


class RenderKeyValuesTest(unittest.TestCase):
    def test_should_lay_each_fact_of_a_detail_page_under_its_name_in_one_panel(self):
        # Arrange
        pairs = (("Task <id>", '<a href="#x">B144</a>'), ("Role", "ada"))

        # Act
        rendered = render_key_values(pairs)

        # Assert
        self.assertEqual(
            rendered,
            '<dl class="panel pad kv"><div><dt>Task &lt;id&gt;</dt><dd><a href="#x">B144</a></dd></div>'
            "<div><dt>Role</dt><dd>ada</dd></div></dl>",
        )
