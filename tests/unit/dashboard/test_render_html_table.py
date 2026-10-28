import unittest

from brigade.dashboard.render_html_table import render_html_table


class RenderHtmlTableTest(unittest.TestCase):
    def test_should_render_the_header_then_one_row_per_line(self):
        # Arrange
        rows = [("1", '<a href="#x">x</a>')]

        # Act
        table = render_html_table(("#", "link"), rows, "nothing")

        # Assert
        self.assertEqual(
            table,
            "<table><thead><tr><th>#</th><th>link</th></tr></thead>"
            '<tbody><tr><td>1</td><td><a href="#x">x</a></td></tr></tbody></table>',
        )

    def test_should_say_what_is_missing_when_there_is_no_row(self):
        # Arrange
        no_row = []

        # Act
        table = render_html_table(("#", "link"), no_row, "no <link>")

        # Assert
        self.assertEqual(table, "<p>no &lt;link&gt;</p>")
