import unittest

from brigade.corpus.read_entity import Entity
from brigade.planning.list_name_collisions import list_name_collisions
from brigade.planning.read_entity_sites import EntitySite
from brigade.planning.read_plan import PlanEntity


class ListNameCollisionsTest(unittest.TestCase):
    def test_should_name_each_planned_entity_the_corpus_already_holds_and_where(self):
        # Arrange
        sites = (
            EntitySite(type="TASK", name="B12", file="corpus/tasks.awawa", line=40),
            EntitySite(type="MILESTONE", name="B12", file="corpus/milestones.awawa", line=3),
        )
        plan = (
            PlanEntity(type="TASK", entity=Entity(name="B12", fields=())),
            PlanEntity(type="TASK", entity=Entity(name="B13", fields=())),
        )

        # Act
        collisions = list_name_collisions(sites, plan)

        # Assert
        self.assertEqual(collisions, ["@TASK.B12 already exists at corpus/tasks.awawa:40"])
