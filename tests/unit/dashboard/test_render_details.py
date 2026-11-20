import unittest

from brigade.dashboard.render_details import render_details


class RenderDetailsTest(unittest.TestCase):
    def test_should_fold_the_content_under_its_summary_escaped(self):
        # Arrange
        content = "<p>the raw document</p>"

        # Act
        rendered = render_details("Errors <raw>", content)

        # Assert
        self.assertEqual(rendered, "<details><summary>Errors &lt;raw&gt;</summary><p>the raw document</p></details>")
