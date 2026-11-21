import unittest

from brigade.dashboard.awawa_address import AwawaAddress
from brigade.dashboard.render_awawa_banner import render_awawa_banner

BOARD_AT_MAIN = AwawaAddress(project="oak", parameters=(("view", "board"), ("type", "TASK"), ("ref", "main")))
READING_OF_OAK = {
    "project": "oak",
    "ref": "main",
    "sha": "de446f3",
    "refs": ["main", "feature/x", "worktree:b42"],
}


class RenderAwawaBannerTest(unittest.TestCase):
    def test_should_name_the_reading_and_offer_the_refs_of_the_project_as_a_selector_with_no_button(self):
        # Act
        fragment = render_awawa_banner(READING_OF_OAK, BOARD_AT_MAIN)

        # Assert
        self.assertEqual(
            fragment,
            '<header class="awawa-banner"><p class="awawa-reading"><strong>oak</strong> at <code>main</code>,'
            ' commit <code>de446f3</code></p><form class="awawa-ref" method="get" data-view="awawa/oak">'
            '<input type="hidden" name="view" value="board"><input type="hidden" name="type" value="TASK">'
            '<span class="field"><label for="awawa-ref">ref</label><select id="awawa-ref" name="ref">'
            '<option value="main" data-href="awawa/oak?view=board&amp;type=TASK&amp;ref=main" selected>main</option>'
            '<option value="feature/x" data-href="awawa/oak?view=board&amp;type=TASK&amp;ref=feature%2Fx">feature/x'
            '</option><option value="worktree:b42" data-href="awawa/oak?view=board&amp;type=TASK&amp;ref=worktree%3Ab42">'
            "worktree:b42</option></select></span></form></header>",
        )

    def test_should_escape_a_ref_holding_markup(self):
        # Arrange
        reading = READING_OF_OAK | {"ref": "<b>", "refs": ["<b>"]}

        # Act
        fragment = render_awawa_banner(reading, BOARD_AT_MAIN)

        # Assert
        self.assertIn("at <code>&lt;b&gt;</code>, commit <code>de446f3</code></p>", fragment)


class RenderAwawaBannerOfAFullShaTest(unittest.TestCase):
    def test_should_shorten_the_commit_read_to_eight_characters(self):
        # Arrange
        reading = {**READING_OF_OAK, "sha": "f23e9bcd0123456789abcdef0123456789abcdef"}

        # Act
        banner = render_awawa_banner(reading, BOARD_AT_MAIN)

        # Assert
        self.assertIn('<code title="f23e9bcd0123456789abcdef0123456789abcdef">f23e9bcd</code>', banner)
