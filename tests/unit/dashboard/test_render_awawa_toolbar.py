import unittest

from brigade.dashboard.awawa_address import AwawaAddress
from brigade.dashboard.render_awawa_toolbar import render_awawa_toolbar

BOARD_OF_THE_TODO_TASKS = AwawaAddress(
    project="oak", parameters=(("view", "board"), ("type", "TASK"), ("filter", "STATUS=todo"))
)
TREE_OF_OAK = AwawaAddress(project="oak", parameters=(("view", "tree"),))
BOARD = {
    "types": ["SCHEMA", "MILESTONE", "TASK"],
    "view": "board",
    "field": "STATUS",
    "fields": ["TITLE", "STATUS", "AFTER"],
    "filter_values": {"STATUS": ["draft", "todo"]},
}
DEPENDENCIES_OF_THE_TASKS = AwawaAddress(project="oak", parameters=(("view", "dependencies"), ("type", "TASK")))
DEPENDENCIES = {
    "types": ["SCHEMA", "MILESTONE", "TASK"],
    "view": "dependencies",
    "field": "AFTER",
    "fields": ["AFTER"],
    "filter_values": {},
}
TREE = {"types": ["SCHEMA", "MILESTONE", "TASK"], "view": "tree", "filter_values": {}}


class RenderAwawaToolbarTest(unittest.TestCase):
    def test_should_offer_each_view_as_a_tab_keeping_the_address_and_select_the_one_shown(self):
        # Act
        fragment = render_awawa_toolbar(BOARD, BOARD_OF_THE_TODO_TASKS)

        # Assert
        self.assertIn(
            '<div class="tabs" role="tablist" aria-label="View">'
            '<a role="tab" href="#awawa/oak?type=TASK&amp;filter=STATUS%3Dtodo&amp;view=tree">Tree</a>'
            '<a role="tab" href="#awawa/oak?type=TASK&amp;filter=STATUS%3Dtodo&amp;view=board" aria-selected="true">'
            "Board</a>"
            '<a role="tab" href="#awawa/oak?type=TASK&amp;filter=STATUS%3Dtodo&amp;view=dependencies">Dependencies</a>'
            '<a role="tab" href="#awawa/oak?type=TASK&amp;filter=STATUS%3Dtodo&amp;view=health">Health</a></div>',
            fragment,
        )

    def test_should_read_the_board_of_the_first_type_of_the_domain_when_the_address_names_no_type(self):
        # Act
        fragment = render_awawa_toolbar(TREE, TREE_OF_OAK)

        # Assert
        self.assertIn('<a role="tab" href="#awawa/oak?type=MILESTONE&amp;view=board">Board</a>', fragment)

    def test_should_offer_the_types_as_a_selector_dropping_the_filters_of_the_type_shown_with_no_button(self):
        # Act
        fragment = render_awawa_toolbar(BOARD, BOARD_OF_THE_TODO_TASKS)

        # Assert
        self.assertIn(
            '<form class="awawa-type" method="get" data-view="awawa/oak">'
            '<input type="hidden" name="view" value="board">'
            '<span class="field"><label for="awawa-type">Type</label><select id="awawa-type" name="type">'
            '<option value="SCHEMA" data-href="awawa/oak?view=board&amp;type=SCHEMA">SCHEMA</option>'
            '<option value="MILESTONE" data-href="awawa/oak?view=board&amp;type=MILESTONE">MILESTONE</option>'
            '<option value="TASK" data-href="awawa/oak?view=board&amp;type=TASK" selected>TASK</option>'
            "</select></span></form>",
            fragment,
        )

    def test_should_offer_the_fields_of_the_type_to_group_the_board_by_as_a_selector_with_no_button(self):
        # Act
        fragment = render_awawa_toolbar(BOARD, BOARD_OF_THE_TODO_TASKS)

        # Assert
        self.assertIn(
            '<form class="awawa-field" method="get" data-view="awawa/oak">'
            '<input type="hidden" name="view" value="board"><input type="hidden" name="type" value="TASK">'
            '<input type="hidden" name="filter" value="STATUS=todo">'
            '<span class="field"><label for="awawa-field">By</label><select id="awawa-field" name="field">'
            '<option value="TITLE" data-href="awawa/oak?view=board&amp;type=TASK&amp;filter=STATUS%3Dtodo&amp;field=TITLE">'
            "TITLE</option>"
            '<option value="STATUS" data-href="awawa/oak?view=board&amp;type=TASK&amp;filter=STATUS%3Dtodo&amp;field=STATUS"'
            " selected>STATUS</option>"
            '<option value="AFTER" data-href="awawa/oak?view=board&amp;type=TASK&amp;filter=STATUS%3Dtodo&amp;field=AFTER">'
            "AFTER</option></select></span></form>",
            fragment,
        )

    def test_should_offer_the_fields_the_dependencies_follow_as_a_selector_with_no_button(self):
        # Act
        fragment = render_awawa_toolbar(DEPENDENCIES, DEPENDENCIES_OF_THE_TASKS)

        # Assert
        self.assertIn(
            '<form class="awawa-field" method="get" data-view="awawa/oak">'
            '<input type="hidden" name="view" value="dependencies"><input type="hidden" name="type" value="TASK">'
            '<span class="field"><label for="awawa-field">Follow</label><select id="awawa-field" name="field">'
            '<option value="AFTER" data-href="awawa/oak?view=dependencies&amp;type=TASK&amp;field=AFTER" selected>AFTER'
            "</option></select></span></form>",
            fragment,
        )

    def test_should_offer_no_field_selector_on_the_tree(self):
        # Act
        fragment = render_awawa_toolbar(TREE, TREE_OF_OAK)

        # Assert
        self.assertNotIn('name="field"', fragment)

    def test_should_offer_a_search_that_holds_the_polling_while_typed_in_with_no_button(self):
        # Act
        fragment = render_awawa_toolbar(BOARD, BOARD_OF_THE_TODO_TASKS)

        # Assert
        self.assertIn(
            '<span class="field"><label for="awawa-search" class="mono">search</label><input type="search"'
            ' id="awawa-search" name="search" value="" placeholder="Search the label, the name or a fact"'
            " data-pauses-poll></span></form>",
            fragment,
        )

    def test_should_offer_a_filter_to_add_through_selectors_not_typed(self):
        # Act
        fragment = render_awawa_toolbar(BOARD, BOARD_OF_THE_TODO_TASKS)

        # Assert
        self.assertIn('<select id="awawa-pick" name="pick">', fragment)
        self.assertNotIn('<input name="filter"', fragment)


class RenderAwawaToolbarAsTheMockupTest(unittest.TestCase):
    def test_should_offer_the_type_on_the_board_and_the_dependencies_alone(self):
        # Act
        toolbar = render_awawa_toolbar(TREE, TREE_OF_OAK)

        # Assert
        self.assertNotIn('name="type"', toolbar)

    def test_should_give_each_choice_of_a_selector_the_address_it_leads_to(self):
        # Act
        toolbar = render_awawa_toolbar(BOARD, BOARD_OF_THE_TODO_TASKS)

        # Assert
        self.assertIn('<option value="MILESTONE" data-href="awawa/oak?view=board&amp;type=MILESTONE">', toolbar)
        self.assertIn(
            '<option value="AFTER" data-href="awawa/oak?view=board&amp;type=TASK&amp;filter=STATUS%3Dtodo&amp;field=AFTER">',
            toolbar,
        )
