import unittest

from brigade.dashboard.awawa_addon_supervisor import AddonAnswer
from brigade.dashboard.awawa_address import AwawaAddress
from brigade.dashboard.render_awawa_tab import render_awawa_tab
from tests.unit.dashboard.forms_collector import FormsCollector
from tests.unit.dashboard.test_render_awawa_board import BOARD
from tests.unit.dashboard.test_render_awawa_card import B1
from tests.unit.dashboard.test_render_awawa_detail import DOCUMENT

BOARD_OF_THE_TASKS = AwawaAddress(project="oak", parameters=(("view", "board"), ("type", "TASK")))
ROOT_B1 = B1 | {"in_cycle": False, "already_above": False, "dependents": []}
BOARD_OF_OAK = BOARD | {
    "fields": ["STATUS"],
    "project": "oak",
    "ref": "main",
    "sha": "de446f3",
    "refs": ["main"],
    "types": ["TASK"],
    "awawa_web": None,
}


class RenderAwawaTabTest(unittest.TestCase):
    def test_should_draw_the_banner_the_toolbar_and_the_view_of_the_document(self):
        # Act
        fragment = render_awawa_tab(AddonAnswer(status=200, document=BOARD_OF_OAK), BOARD_OF_THE_TASKS)

        # Assert
        self.assertIn('</header><header class="awawa-banner">', fragment)
        self.assertIn('</header><div class="awawa-toolbar">', fragment)
        self.assertIn('<div class="awawa-body"><div class="awawa-view"><div class="awawa-board">', fragment)

    def test_should_draw_the_view_named_by_the_document(self):
        # Arrange
        rows = [
            ("tree", {"view": "tree", "domain": [], "schema": []}, '<div class="awawa-view"><div class="empty-state">'),
            ("dependencies", {"view": "dependencies", "field": "AFTER", "roots": [ROOT_B1]}, "awawa-dependencies"),
            (
                "health",
                {"view": "health", "errors": 0, "warnings": 0, "unresolved": 0, "entities": [], "files": []},
                "awawa-health",
            ),
        ]
        for view, drawn, expected in rows:
            with self.subTest(view=view):
                # Act
                fragment = render_awawa_tab(AddonAnswer(status=200, document=BOARD_OF_OAK | drawn), BOARD_OF_THE_TASKS)

                # Assert
                self.assertIn(expected, fragment)

    def test_should_open_the_detail_panel_beside_the_view(self):
        # Arrange
        detailed = BOARD_OF_OAK | {"detail": DOCUMENT["detail"]}

        # Act
        fragment = render_awawa_tab(AddonAnswer(status=200, document=detailed), BOARD_OF_THE_TASKS)

        # Assert
        self.assertIn('</div><aside class="awawa-detail">', fragment)

    def test_should_show_the_filters_in_force_as_chips(self):
        # Arrange
        filtered = BOARD_OF_THE_TASKS.adding("filter", "STATUS=todo")

        # Act
        fragment = render_awawa_tab(AddonAnswer(status=200, document=BOARD_OF_OAK), filtered)

        # Assert
        self.assertIn('</div><nav class="chips">', fragment)

    def test_should_offer_no_action_writing_the_corpus(self):
        # Arrange
        forms = FormsCollector()

        # Act
        fragment = render_awawa_tab(AddonAnswer(status=200, document=BOARD_OF_OAK), BOARD_OF_THE_TASKS)

        # Assert
        forms.feed(fragment)
        self.assertEqual(forms.methods, ["get", "get", "get", "get"])
        self.assertEqual(forms.writing_attributes, [])
        self.assertNotIn("data-post", fragment)
        self.assertNotIn("Clean", fragment)
        self.assertNotIn("Change Colour", fragment)
        self.assertNotIn("Arrange Columns", fragment)

    def test_should_say_that_a_project_holds_no_awawa_corpus(self):
        # Arrange
        answer = AddonAnswer(status=404, document={"error": "@PROJECT.shop holds no awawa corpus"})

        # Act
        fragment = render_awawa_tab(answer, AwawaAddress(project="shop"))

        # Assert
        self.assertEqual(
            fragment,
            '<div class="empty-state"><p class="empty-why">shop has no awawa corpus.</p>'
            '<p class="empty-fill">A corpus awawa finds in the folder of the project would fill this tab.</p></div>',
        )

    def test_should_say_that_the_addon_stopped_with_its_error(self):
        # Arrange
        answer = AddonAnswer(status=503, document={"error": "the awawa addon did not start: awawa: not found"})

        # Act
        fragment = render_awawa_tab(answer, BOARD_OF_THE_TASKS)

        # Assert
        self.assertEqual(
            fragment,
            '<div class="empty-state"><p class="empty-why">The awawa addon stopped.</p>'
            '<p class="empty-fill">the awawa addon did not start: awawa: not found</p></div>',
        )

    def test_should_say_that_the_corpus_could_not_be_read_at_the_address(self):
        # Arrange
        answer = AddonAnswer(status=500, document={"error": "--view board reads the entities of --type"})

        # Act
        fragment = render_awawa_tab(answer, BOARD_OF_THE_TASKS)

        # Assert
        self.assertEqual(
            fragment,
            '<div class="empty-state"><p class="empty-why">The corpus could not be read at this address.</p>'
            '<p class="empty-fill">--view board reads the entities of --type</p></div>',
        )


class RenderAwawaTabHeadTest(unittest.TestCase):
    def test_should_open_on_the_page_head_of_the_tab_before_its_banner(self):
        # Act
        fragment = render_awawa_tab(AddonAnswer(status=200, document=BOARD_OF_OAK), BOARD_OF_THE_TASKS)

        # Assert
        self.assertTrue(
            fragment.startswith(
                '<header class="page-head"><div><h1>awawa</h1><p class="lede">The specification of the project, read-only: its entities as a tree, a board and a dependency tree, and what awawa lint finds.</p></div>'
                '<p class="fresh num" data-fresh>refreshes every 5 s</p></header><header class="awawa-banner">'
            )
        )
