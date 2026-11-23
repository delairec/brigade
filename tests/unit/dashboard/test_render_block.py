import unittest

from brigade.dashboard.render_block import Block, render_block


class RenderBlockTest(unittest.TestCase):
    def test_should_set_what_a_section_is_for_beside_its_heading_above_its_body(self):
        # Arrange
        block = Block(title="Tasks <all>", lede="Each task & what it cost.", body="<table></table>")

        # Act
        rendered = render_block(block)

        # Assert
        self.assertEqual(
            rendered,
            '<section class="block"><div class="block-head"><h2>Tasks &lt;all&gt;</h2>'
            "<p>Each task &amp; what it cost.</p></div><table></table></section>",
        )

    def test_should_leave_the_heading_alone_when_the_section_says_nothing_beside_it(self):
        # Arrange
        no_lede = ""
        block = Block(title="Events", lede=no_lede, body="<p>none</p>")

        # Act
        rendered = render_block(block)

        # Assert
        self.assertEqual(
            rendered, '<section class="block"><div class="block-head"><h2>Events</h2></div><p>none</p></section>'
        )
