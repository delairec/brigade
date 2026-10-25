import unittest

from brigade.corpus.read_entity import Entity, EntityField
from brigade.tick.actions import CollectCheckRuns
from brigade.tick.plan_connectors import plan_connectors


def create_project(status: str, forge: str) -> Entity:
    return Entity(name="oak", fields=(EntityField(name="STATUS", value=status), EntityField(name="FORGE", value=forge)))


class PlanConnectorsTest(unittest.TestCase):
    def test_should_collect_the_check_runs_of_an_active_project_on_github(self):
        # Act
        actions = plan_connectors((create_project("active", "github"),))

        # Assert
        self.assertEqual(actions, (CollectCheckRuns(project="oak"),))

    def test_should_collect_nothing_from_a_paused_project_or_a_project_with_no_forge(self):
        for status, forge in [("paused", "github"), ("active", "none")]:
            with self.subTest(status=status, forge=forge):
                # Act
                actions = plan_connectors((create_project(status, forge),))

                # Assert
                self.assertEqual(actions, ())
