import unittest

from brigade.corpus.read_entities import Entity, EntityField
from brigade.system.run_process import ProcessRequest
from brigade.waves.locate_project_main import locate_project_main
from tests.unit.scripted_processes import ScriptedProcesses

REPOSITORY = "/srv/shop"
FORGE_ENVIRONMENT = {"GH_TOKEN": "token-of-the-build-slot"}


def _read_forge_environment(slot: str) -> dict:
    return FORGE_ENVIRONMENT


def _create_project(forge: str) -> Entity:
    return Entity(
        name="shop",
        fields=(
            EntityField(name="PATH", value=REPOSITORY),
            EntityField(name="MAIN", value="trunk"),
            EntityField(name="FORGE", value=forge),
        ),
    )


class LocateProjectMainTest(unittest.TestCase):
    def setUp(self):
        self.processes = ScriptedProcesses()
        self.processes.answer(("git", "fetch", "--quiet", "origin", "trunk"))

    def test_should_locate_the_main_branch_of_the_forge_on_github(self):
        # Arrange
        project = _create_project("github")

        # Act
        main = locate_project_main(self.processes, project, _read_forge_environment)

        # Assert
        self.assertEqual(main, "origin/trunk")

    def test_should_fetch_the_main_branch_with_the_environment_of_the_forge_on_github(self):
        # Arrange
        project = _create_project("github")

        # Act
        locate_project_main(self.processes, project, _read_forge_environment)

        # Assert
        self.assertEqual(
            self.processes.requests,
            [
                ProcessRequest(
                    argv=("git", "fetch", "--quiet", "origin", "trunk"),
                    cwd=REPOSITORY,
                    timeout_s=120.0,
                    environment=FORGE_ENVIRONMENT,
                )
            ],
        )

    def test_should_keep_the_local_main_branch_without_a_forge(self):
        # Arrange
        project = _create_project("none")

        # Act
        main = locate_project_main(self.processes, project, _read_forge_environment)

        # Assert
        self.assertEqual((main, self.processes.requests), ("trunk", []))
