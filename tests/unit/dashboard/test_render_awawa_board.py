import unittest

from brigade.dashboard.awawa_address import AwawaAddress
from brigade.dashboard.render_awawa_board import render_awawa_board
from tests.unit.dashboard.test_render_awawa_card import B1, MARKUP

BOARD_OF_THE_TASKS = AwawaAddress(project="oak", parameters=(("view", "board"), ("type", "TASK")))
NO_ENTITY = []
BOARD = {
    "view": "board",
    "field": "STATUS",
    "columns": [
        {"label": "draft", "value": "draft", "entities": NO_ENTITY},
        {"label": "todo", "value": "todo", "entities": [B1]},
        {"label": "Others (2)", "value": None, "entities": [B1 | {"value": "ada"}, B1 | {"value": "bilal"}]},
    ],
}


class RenderAwawaBoardTest(unittest.TestCase):
    def test_should_draw_one_column_per_value_in_the_order_of_the_document(self):
        # Act
        fragment = render_awawa_board(BOARD, BOARD_OF_THE_TASKS)

        # Assert
        self.assertIn(
            '<div class="awawa-board"><section class="awawa-column"><h3>draft <span class="awawa-count">0</span></h3>'
            '<ul class="awawa-cards"></ul></section><section class="awawa-column">'
            '<h3>todo <span class="awawa-count">1</span></h3><ul class="awawa-cards"><li><div class="awawa-card">',
            fragment,
        )

    def test_should_cap_the_columns_with_the_others_column(self):
        # Act
        fragment = render_awawa_board(BOARD, BOARD_OF_THE_TASKS)

        # Assert
        self.assertIn('<h3>Others (2) <span class="awawa-count">2</span></h3>', fragment)

    def test_should_escape_a_column_holding_markup(self):
        # Arrange
        board = BOARD | {"columns": [{"label": MARKUP, "value": MARKUP, "entities": NO_ENTITY}]}

        # Act
        fragment = render_awawa_board(board, BOARD_OF_THE_TASKS)

        # Assert
        self.assertIn(
            '<h3>&quot;&gt;&lt;script&gt;alert(1)&lt;/script&gt; <span class="awawa-count">0</span></h3>', fragment
        )
