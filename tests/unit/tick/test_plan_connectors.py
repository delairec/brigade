import unittest

from brigade.corpus.read_entity import Entity, EntityField
from brigade.tick.actions import CollectCheckRuns, CollectReviewThreads
from brigade.tick.plan_connectors import plan_connectors


def create_project(name: str, status: str, forge: str) -> Entity:
    return Entity(name=name, fields=(EntityField(name="STATUS", value=status), EntityField(name="FORGE", value=forge)))


class PlanConnectorsTest(unittest.TestCase):
    def test_should_collect_the_check_runs_and_the_review_threads_of_every_active_project_on_github(self):
        # Arrange
        projects = (create_project("oak", "active", "github"), create_project("elm", "active", "github"))

        # Act
        actions = plan_connectors(projects)

        # Assert
        self.assertEqual(
            actions,
            (
                CollectCheckRuns(project="oak"),
                CollectReviewThreads(project="oak"),
                CollectCheckRuns(project="elm"),
                CollectReviewThreads(project="elm"),
            ),
        )

    def test_should_collect_nothing_from_a_paused_project_or_a_project_with_no_forge(self):
        rows = [("paused", "github"), ("active", "none")]
        for status, forge in rows:
            with self.subTest(status=status, forge=forge):
                # Arrange
                projects = (create_project("oak", status, forge),)

                # Act
                actions = plan_connectors(projects)

                # Assert
                self.assertEqual(actions, ())
