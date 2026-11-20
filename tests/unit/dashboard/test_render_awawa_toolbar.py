import unittest

from brigade.dashboard.awawa_address import AwawaAddress
from brigade.dashboard.render_awawa_toolbar import render_awawa_toolbar

BOARD_OF_THE_TODO_TASKS = AwawaAddress(
    project="oak", parameters=(("view", "board"), ("type", "TASK"), ("filter", "STATUS=todo"))
)
TREE_OF_OAK = AwawaAddress(project="oak", parameters=(("view", "tree"),))
BOARD = {"types": ["SCHEMA", "MILESTONE", "TASK"], "view": "board", "field": "STATUS"}
TREE = {"types": ["SCHEMA", "MILESTONE", "TASK"], "view": "tree"}


class RenderAwawaToolbarTest(unittest.TestCase):
    def test_should_link_each_view_keeping_the_address_and_mark_the_one_shown(self):
        # Act
        fragment = render_awawa_toolbar(BOARD, BOARD_OF_THE_TODO_TASKS)

        # Assert
        self.assertIn(
            '<nav class="awawa-views"><a href="#awawa/oak?type=TASK&amp;filter=STATUS%3Dtodo&amp;view=tree">Tree</a>'
            '<a href="#awawa/oak?type=TASK&amp;filter=STATUS%3Dtodo&amp;view=board" aria-current="true">Board</a>'
            '<a href="#awawa/oak?type=TASK&amp;filter=STATUS%3Dtodo&amp;view=dependencies">Dependencies</a>'
            '<a href="#awawa/oak?type=TASK&amp;filter=STATUS%3Dtodo&amp;view=health">Health</a></nav>',
            fragment,
        )

    def test_should_read_the_board_of_the_first_type_of_the_domain_when_the_address_names_no_type(self):
        # Act
        fragment = render_awawa_toolbar(TREE, TREE_OF_OAK)

        # Assert
        self.assertIn('<a href="#awawa/oak?type=MILESTONE&amp;view=board">Board</a>', fragment)

    def test_should_link_each_type_dropping_the_filters_of_the_type_shown(self):
        # Act
        fragment = render_awawa_toolbar(BOARD, BOARD_OF_THE_TODO_TASKS)

        # Assert
        self.assertIn(
            '<nav class="awawa-types"><a href="#awawa/oak?view=board&amp;type=SCHEMA">SCHEMA</a>'
            '<a href="#awawa/oak?view=board&amp;type=MILESTONE">MILESTONE</a>'
            '<a href="#awawa/oak?view=board&amp;type=TASK" aria-current="true">TASK</a></nav>',
            fragment,
        )

    def test_should_offer_the_field_of_the_board_on_the_board_alone(self):
        # Arrange
        rows = [
            ("the board", BOARD, BOARD_OF_THE_TODO_TASKS, True),
            ("the tree", TREE, TREE_OF_OAK, False),
        ]
        for case, document, address, offered in rows:
            with self.subTest(case):
                # Act
                fragment = render_awawa_toolbar(document, address)

                # Assert
                self.assertEqual('<label>Field <input name="field" value="STATUS"></label>' in fragment, offered)

    def test_should_offer_the_search_and_a_filter_to_add(self):
        # Act
        fragment = render_awawa_toolbar(BOARD, BOARD_OF_THE_TODO_TASKS)

        # Assert
        self.assertIn(
            '<label>Search <input type="search" name="search" value=""></label>'
            '<label>Filter <input name="filter" placeholder="FIELD=value"></label><button>Apply</button>',
            fragment,
        )
