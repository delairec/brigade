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
    def test_should_name_the_reading_and_offer_the_refs_of_the_project_or_one_typed(self):
        # Act
        fragment = render_awawa_banner(READING_OF_OAK, BOARD_AT_MAIN)

        # Assert
        self.assertEqual(
            fragment,
            '<header class="awawa-banner"><p class="awawa-reading"><strong>oak</strong> at <code>main</code>,'
            ' commit <code>de446f3</code></p><form class="awawa-ref" method="get" data-view="awawa/oak">'
            '<input type="hidden" name="view" value="board"><input type="hidden" name="type" value="TASK">'
            '<label>Ref <input name="ref" list="awawa-refs" value="main"></label><datalist id="awawa-refs">'
            '<option value="main"></option><option value="feature/x"></option>'
            '<option value="worktree:b42"></option></datalist><button>Read</button></form></header>',
        )

    def test_should_escape_a_ref_holding_markup(self):
        # Arrange
        reading = READING_OF_OAK | {"ref": "<b>", "refs": ["<b>"]}

        # Act
        fragment = render_awawa_banner(reading, BOARD_AT_MAIN)

        # Assert
        self.assertIn("at <code>&lt;b&gt;</code>, commit <code>de446f3</code></p>", fragment)
