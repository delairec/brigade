import unittest

from brigade.corpus.read_entities import Entity, EntityField
from brigade.errors import CommandFailed
from brigade.system.run_process import ProcessRequest
from brigade.waves.is_milestone_branch_off_the_forge import RecordedMilestoneBranch, is_milestone_branch_off_the_forge
from tests.unit.scripted_processes import ScriptedProcesses

REPOSITORY = "/srv/shop"
BRANCH = "integration/milestone-integration-branch"
LS_REMOTE = ("git", "ls-remote", "--quiet", "--exit-code", "--heads", "origin", f"refs/heads/{BRANCH}")
FORGE_ENVIRONMENT = {"GH_TOKEN": "token-of-the-cli-key"}
REMOTE_BRANCH_FOUND = 0
REMOTE_BRANCH_NOT_FOUND = 2
REMOTE_UNREACHABLE = 128


def _read_forge_environment(slot: str) -> dict:
    return FORGE_ENVIRONMENT


def _create_project(forge: str) -> Entity:
    return Entity(
        name="shop",
        fields=(EntityField(name="PATH", value=REPOSITORY), EntityField(name="FORGE", value=forge)),
    )


class IsMilestoneBranchOffTheForgeTestCase(unittest.TestCase):
    def setUp(self):
        self.processes = ScriptedProcesses()

    def ask(self, forge: str) -> bool:
        recorded = RecordedMilestoneBranch(
            project=_create_project(forge), branch=BRANCH, read_environment=_read_forge_environment
        )
        return is_milestone_branch_off_the_forge(self.processes, recorded)


class IsMilestoneBranchOffTheGithubForgeTest(IsMilestoneBranchOffTheForgeTestCase):
    def test_should_tell_whether_the_forge_holds_the_branch(self):
        for exit_code, expected in [(REMOTE_BRANCH_FOUND, False), (REMOTE_BRANCH_NOT_FOUND, True)]:
            with self.subTest(exit_code=exit_code):
                # Arrange
                self.processes.answer(LS_REMOTE, exit_code=exit_code)

                # Act
                off_the_forge = self.ask("github")

                # Assert
                self.assertEqual(off_the_forge, expected)

    def test_should_ask_the_forge_under_the_environment_of_the_cli_key(self):
        # Arrange
        self.processes.answer(LS_REMOTE)

        # Act
        self.ask("github")

        # Assert
        self.assertEqual(
            self.processes.requests,
            [
                ProcessRequest(
                    argv=LS_REMOTE,
                    cwd=REPOSITORY,
                    timeout_s=60.0,
                    acceptable_exit_codes=(REMOTE_BRANCH_FOUND, REMOTE_BRANCH_NOT_FOUND),
                    environment=FORGE_ENVIRONMENT,
                )
            ],
        )

    def test_should_refuse_to_answer_when_the_forge_cannot_be_reached(self):
        # Arrange
        self.processes.answer(LS_REMOTE, exit_code=REMOTE_UNREACHABLE, stderr="fatal: unable to access")

        # Act
        with self.assertRaises(CommandFailed) as refusal:
            self.ask("github")

        # Assert
        self.assertEqual(str(refusal.exception), f"{' '.join(LS_REMOTE)} exited 128: fatal: unable to access")


class IsMilestoneBranchOffTheForgeOfAProjectWithoutAForgeTest(IsMilestoneBranchOffTheForgeTestCase):
    def test_should_answer_the_branch_held_and_ask_nothing(self):
        # Act
        off_the_forge = self.ask("none")

        # Assert
        self.assertFalse(off_the_forge)
        self.assertEqual(self.processes.requests, [])


if __name__ == "__main__":
    unittest.main()
