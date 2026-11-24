import unittest

from brigade.dashboard.awawa_address import AwawaAddress
from brigade.dashboard.render_awawa_tree import render_awawa_tree
from tests.unit.dashboard.test_render_awawa_card import B1

TREE_OF_OAK = AwawaAddress(project="oak", parameters=(("view", "tree"),))
B2 = B1 | {"target": "@TASK.B2", "code": "B2", "status": "implemented"}
PROJECT_OAK = B1 | {"type": "PROJECT", "target": "@PROJECT.oak", "code": "oak", "status": None}
SCHEMA_TASK = B1 | {"type": "SCHEMA", "target": "@SCHEMA.TASK", "code": "TASK", "status": None}
TREE = {
    "view": "tree",
    "domain": [
        {
            "type": "TASK",
            "total": 28,
            "groups": [
                {"status": "todo", "collapsed": False, "entities": [B1]},
                {"status": "implemented", "collapsed": True, "entities": [B2]},
                {"status": None, "collapsed": False, "entities": [B1 | {"status": None}]},
            ],
        },
        {"type": "PROJECT", "total": 1, "entities": [PROJECT_OAK]},
    ],
    "schema": [{"type": "SCHEMA", "total": 1, "entities": [SCHEMA_TASK]}],
}


class RenderAwawaTreeTest(unittest.TestCase):
    def test_should_open_a_group_of_the_lifecycle_and_count_its_entities(self):
        # Act
        fragment = render_awawa_tree(TREE, TREE_OF_OAK)

        # Assert
        self.assertIn(
            '<section class="awawa-type"><h2>Task <small>3 of 28</small></h2><details class="awawa-group" open>'
            '<summary>todo <span class="awawa-count">1</span></summary><ul class="awawa-cards"><li>'
            '<div class="awawa-card">',
            fragment,
        )

    def test_should_collapse_the_last_group_of_the_lifecycle_after_the_ones_before_it(self):
        # Act
        fragment = render_awawa_tree(TREE, TREE_OF_OAK)

        # Assert
        self.assertIn(
            '</ul></details><details class="awawa-group"><summary>implemented <span class="awawa-count">1</span>',
            fragment,
        )

    def test_should_count_the_entities_kept_of_a_type_out_of_all_it_holds(self):
        # Act
        fragment = render_awawa_tree(TREE, TREE_OF_OAK)

        # Assert
        self.assertIn("<h2>Task <small>3 of 28</small></h2>", fragment)

    def test_should_count_once_the_entities_of_a_type_kept_whole(self):
        # Act
        fragment = render_awawa_tree(TREE, TREE_OF_OAK)

        # Assert
        self.assertIn("<h2>Project <small>1</small></h2>", fragment)

    def test_should_name_the_group_of_the_entities_without_status(self):
        # Act
        fragment = render_awawa_tree(TREE, TREE_OF_OAK)

        # Assert
        self.assertIn('<summary>no status <span class="awawa-count">1</span></summary>', fragment)

    def test_should_list_a_type_without_lifecycle_in_one_list(self):
        # Act
        fragment = render_awawa_tree(TREE, TREE_OF_OAK)

        # Assert
        self.assertIn(
            '<section class="awawa-type"><h2>Project <small>1</small></h2><ul class="awawa-cards"><li><div class="awawa-card">',
            fragment,
        )

    def test_should_fold_the_types_of_the_schema_below_the_domain(self):
        # Act
        fragment = render_awawa_tree(TREE, TREE_OF_OAK)

        # Assert
        self.assertIn(
            '<details class="awawa-schema"><summary>Schema</summary><section class="awawa-type"><h2>Schema <small>1</small></h2>',
            fragment,
        )

    def test_should_say_that_no_entity_matches_an_address_keeping_none(self):
        # Arrange
        nothing_kept = {"view": "tree", "domain": [], "schema": []}

        # Act
        fragment = render_awawa_tree(nothing_kept, TREE_OF_OAK)

        # Assert
        self.assertEqual(
            fragment,
            '<div class="empty-state"><p class="empty-why">No entity matches this address.</p>'
            '<p class="empty-fill">Clear the filters and the search to see the whole corpus.</p></div>',
        )
