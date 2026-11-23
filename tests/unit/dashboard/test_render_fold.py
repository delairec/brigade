import unittest

from brigade.dashboard.render_fold import Fold, render_fold


class RenderFoldTest(unittest.TestCase):
    def test_should_fold_a_body_under_its_summary_and_what_it_holds(self):
        # Arrange
        fold = Fold(summary="Show the <events>", detail="41 task.state & 18 others", body="<table></table>")

        # Act
        rendered = render_fold(fold)

        # Assert
        self.assertEqual(
            rendered,
            '<details class="fold"><summary>Show the &lt;events&gt; <span>· 41 task.state &amp; 18 others</span>'
            "</summary><table></table></details>",
        )

    def test_should_open_a_fold_the_page_shows_unfolded(self):
        # Arrange
        no_detail = ""
        fold = Fold(summary="B91", detail=no_detail, body="<ol></ol>", opened=True)

        # Act
        rendered = render_fold(fold)

        # Assert
        self.assertEqual(rendered, '<details class="fold" open><summary>B91</summary><ol></ol></details>')
