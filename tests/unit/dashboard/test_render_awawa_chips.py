import unittest

from brigade.dashboard.awawa_address import AwawaAddress
from brigade.dashboard.render_awawa_chips import render_awawa_chips

FILTERED_BOARD = AwawaAddress(
    project="oak",
    parameters=(
        ("view", "board"),
        ("type", "TASK"),
        ("filter", "STATUS=todo"),
        ("filter", "ROLE=ada"),
        ("search", "board"),
    ),
)


class RenderAwawaChipsTest(unittest.TestCase):
    def test_should_show_each_filter_in_force_as_a_chip_its_link_removes_with_clear_all(self):
        # Act
        fragment = render_awawa_chips(FILTERED_BOARD)

        # Assert
        self.assertEqual(
            fragment,
            '<nav class="chips">'
            '<a class="chip" href="#awawa/oak?view=board&amp;type=TASK&amp;filter=ROLE%3Dada&amp;search=board"'
            ' title="Remove this filter">Task · Status: todo ✕</a>'
            '<a class="chip" href="#awawa/oak?view=board&amp;type=TASK&amp;filter=STATUS%3Dtodo&amp;search=board"'
            ' title="Remove this filter">Task · Role: ada ✕</a>'
            '<a class="chip" href="#awawa/oak?view=board&amp;type=TASK&amp;filter=STATUS%3Dtodo&amp;filter=ROLE%3Dada"'
            ' title="Remove this filter">Search: board ✕</a>'
            '<a class="muted" href="#awawa/oak?view=board&amp;type=TASK">Clear all</a></nav>',
        )

    def test_should_gather_the_values_in_force_for_one_field_in_one_chip_removing_them_all(self):
        # Arrange
        address = AwawaAddress(
            project="oak",
            parameters=(("view", "board"), ("type", "TASK"), ("filter", "STATUS=draft"), ("filter", "STATUS=todo")),
        )

        # Act
        fragment = render_awawa_chips(address)

        # Assert
        self.assertIn(
            '<a class="chip" href="#awawa/oak?view=board&amp;type=TASK" title="Remove this filter">'
            "Task · Status: draft, todo ✕</a>",
            fragment,
        )

    def test_should_show_no_chip_when_no_filter_is_in_force(self):
        # Arrange
        unfiltered = AwawaAddress(project="oak", parameters=(("view", "board"), ("type", "TASK")))

        # Act
        fragment = render_awawa_chips(unfiltered)

        # Assert
        self.assertEqual(fragment, "")

    def test_should_escape_a_filter_holding_markup(self):
        # Arrange
        address = AwawaAddress(project="oak", parameters=(("filter", "STATUS=<b>"),))

        # Act
        fragment = render_awawa_chips(address)

        # Assert
        self.assertIn(">Status: &lt;b&gt; ✕</a>", fragment)
