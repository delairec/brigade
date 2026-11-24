import unittest

from brigade.dashboard.awawa_address import AwawaAddress
from brigade.dashboard.render_awawa_filter_picker import render_awawa_filter_picker

BOARD_OF_THE_TODO_TASKS = AwawaAddress(
    project="oak", parameters=(("view", "board"), ("type", "TASK"), ("filter", "STATUS=todo"))
)
STATUS_PICKED = AwawaAddress(
    project="oak", parameters=(("view", "board"), ("type", "TASK"), ("filter", "STATUS=todo"), ("pick", "STATUS"))
)
VALUES = {"STATUS": ["draft", "implemented", "todo"], "ROLE": ["ada"]}
NO_TYPE_READ = {}


class RenderAwawaFilterPickerTest(unittest.TestCase):
    def test_should_offer_the_fields_to_filter_by_as_a_selector_each_choice_leading_to_its_values(self):
        # Act
        fragment = render_awawa_filter_picker(VALUES, BOARD_OF_THE_TODO_TASKS)

        # Assert
        self.assertEqual(
            fragment,
            '<form class="awawa-filter" method="get" data-view="awawa/oak">'
            '<input type="hidden" name="view" value="board"><input type="hidden" name="type" value="TASK">'
            '<input type="hidden" name="filter" value="STATUS=todo">'
            '<span class="field"><label for="awawa-pick">Filter</label><select id="awawa-pick" name="pick">'
            '<option value="" selected>Add a filter</option>'
            '<option value="STATUS" data-href="awawa/oak?view=board&amp;type=TASK&amp;filter=STATUS%3Dtodo&amp;pick=STATUS">'
            "STATUS</option>"
            '<option value="ROLE" data-href="awawa/oak?view=board&amp;type=TASK&amp;filter=STATUS%3Dtodo&amp;pick=ROLE">'
            "ROLE</option></select></span></form>",
        )

    def test_should_offer_the_values_of_the_field_picked_but_those_in_force_each_adding_its_filter(self):
        # Act
        fragment = render_awawa_filter_picker(VALUES, STATUS_PICKED)

        # Assert
        self.assertIn(
            '<option value="">Add a filter</option><option value="STATUS" data-href="awawa/oak?view=board&amp;type=TASK'
            '&amp;filter=STATUS%3Dtodo&amp;pick=STATUS" selected>STATUS</option>',
            fragment,
        )
        self.assertIn(
            '<span class="field"><label for="awawa-value">STATUS</label><select id="awawa-value" name="filter">'
            '<option value="" selected>Choose a value</option>'
            '<option value="STATUS=draft" data-href="awawa/oak?view=board&amp;type=TASK&amp;filter=STATUS%3Dtodo'
            '&amp;filter=STATUS%3Ddraft">draft</option>'
            '<option value="STATUS=implemented" data-href="awawa/oak?view=board&amp;type=TASK&amp;filter=STATUS%3Dtodo'
            '&amp;filter=STATUS%3Dimplemented">implemented</option></select></span></form>',
            fragment,
        )

    def test_should_offer_no_value_for_a_field_picked_the_type_does_not_hold(self):
        # Arrange
        address = AwawaAddress(project="oak", parameters=(("view", "board"), ("type", "TASK"), ("pick", "NOPE")))

        # Act
        fragment = render_awawa_filter_picker(VALUES, address)

        # Assert
        self.assertNotIn('name="filter"', fragment)

    def test_should_offer_no_filter_when_no_type_is_read(self):
        # Act
        fragment = render_awawa_filter_picker(NO_TYPE_READ, BOARD_OF_THE_TODO_TASKS)

        # Assert
        self.assertEqual(fragment, "")
