import unittest
from unittest import mock

from brigade.commands.project_status import _build_rewrite
from brigade.corpus.read_entity import Entity, EntityField
from brigade.errors import BrigadeError
from brigade.registry.change_registry import REGISTRY_FILE


def make_entity(name: str, status: str = "active") -> Entity:
    return Entity(
        name=name,
        fields=(EntityField(name="STATUS", value=status), EntityField(name="PATH", value=f"/srv/{name}")),
    )


class BuildRewriteTest(unittest.TestCase):
    def test_should_raise_when_the_project_block_is_not_in_the_text(self):
        # Arrange
        runtime = mock.Mock()
        runtime.run_process = mock.Mock()
        project = make_entity("alpha")
        with mock.patch("brigade.commands.project_status.read_projects", return_value=(project,)):
            rewrite = _build_rewrite(runtime, "alpha", "paused")

            # Act
            with self.assertRaises(BrigadeError) as raised:
                rewrite("PROJECT beta\n\tSTATUS active\n")

        # Assert
        self.assertEqual(str(raised.exception), f"@PROJECT.alpha is not written in {REGISTRY_FILE}")

    def test_should_return_none_when_the_project_already_has_the_status(self):
        # Arrange
        runtime = mock.Mock()
        runtime.run_process = mock.Mock()
        project = make_entity("alpha", status="paused")
        with mock.patch("brigade.commands.project_status.read_projects", return_value=(project,)):
            rewrite = _build_rewrite(runtime, "alpha", "paused")

            # Act
            result = rewrite("PROJECT alpha\n\tSTATUS paused\n")

        # Assert
        self.assertIsNone(result)

    def test_should_rewrite_the_status_of_the_project(self):
        # Arrange
        runtime = mock.Mock()
        runtime.run_process = mock.Mock()
        project = make_entity("alpha", status="active")
        with mock.patch("brigade.commands.project_status.read_projects", return_value=(project,)):
            rewrite = _build_rewrite(runtime, "alpha", "paused")

            # Act
            result = rewrite('PROJECT alpha\n\tSTATUS active\n\tPATH "/srv/alpha"\n')

        # Assert
        self.assertEqual(result, 'PROJECT alpha\n\tSTATUS paused\n\tPATH "/srv/alpha"\n')
