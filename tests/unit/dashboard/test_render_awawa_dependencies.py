import unittest

from brigade.dashboard.awawa_address import AwawaAddress
from brigade.dashboard.render_awawa_dependencies import render_awawa_dependencies
from tests.unit.dashboard.test_render_awawa_card import B1, MARKUP

DEPENDENCIES_OF_THE_TASKS = AwawaAddress(project="oak", parameters=(("view", "dependencies"), ("type", "TASK")))
B2 = B1 | {"target": "@TASK.B2", "code": "B2"}
NO_DEPENDENT = []
DEPENDENCIES = {
    "view": "dependencies",
    "field": "AFTER",
    "roots": [
        B1
        | {
            "in_cycle": False,
            "already_above": False,
            "dependents": [
                B2
                | {
                    "in_cycle": True,
                    "already_above": False,
                    "dependents": [B1 | {"in_cycle": True, "already_above": True, "dependents": NO_DEPENDENT}],
                }
            ],
        }
    ],
}


class RenderAwawaDependenciesTest(unittest.TestCase):
    def test_should_say_which_field_the_dependencies_are_read_from(self):
        # Act
        fragment = render_awawa_dependencies(DEPENDENCIES, DEPENDENCIES_OF_THE_TASKS)

        # Assert
        self.assertIn(
            '<div class="awawa-dependencies"><p class="awawa-reading">'
            "Each entity stands above the entities naming it in AFTER.</p>",
            fragment,
        )

    def test_should_nest_the_dependents_of_an_entity_below_it(self):
        # Act
        fragment = render_awawa_dependencies(DEPENDENCIES, DEPENDENCIES_OF_THE_TASKS)

        # Assert
        self.assertIn('</div><ul class="awawa-nodes"><li><div class="awawa-card">', fragment)

    def test_should_flag_an_entity_of_a_cycle_and_one_already_shown_above(self):
        # Act
        fragment = render_awawa_dependencies(DEPENDENCIES, DEPENDENCIES_OF_THE_TASKS)

        # Assert
        self.assertIn(
            '<span class="awawa-flag tone-failed">cycle</span><span class="awawa-flag">shown above</span></li>',
            fragment,
        )

    def test_should_escape_a_field_holding_markup(self):
        # Act
        fragment = render_awawa_dependencies(DEPENDENCIES | {"field": MARKUP}, DEPENDENCIES_OF_THE_TASKS)

        # Assert
        self.assertIn("naming it in &quot;&gt;&lt;script&gt;alert(1)&lt;/script&gt;.</p>", fragment)

    def test_should_say_that_no_entity_matches_an_address_keeping_none(self):
        # Arrange
        nothing_kept = {"view": "dependencies", "field": "AFTER", "roots": []}

        # Act
        fragment = render_awawa_dependencies(nothing_kept, DEPENDENCIES_OF_THE_TASKS)

        # Assert
        self.assertIn('<p class="empty-why">No entity matches this address.</p>', fragment)
