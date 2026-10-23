import unittest
from pathlib import Path

from brigade.git.find_remote_branch import RemoteBranch, find_remote_branch
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

LS_REMOTE = ("git", "ls-remote", "--quiet", "--exit-code", "--heads", "origin", "refs/heads/integration/shop_w2")
FORGE_ENVIRONMENT = {"GH_TOKEN": "token-of-octo-bot"}


class FindRemoteBranchTest(unittest.TestCase):
    def test_should_tell_whether_the_branch_exists_on_the_remote(self):
        for exit_code, expected in [(0, True), (2, False)]:
            with self.subTest(exit_code=exit_code):
                # Arrange
                git = RecordingProcessRunner({LS_REMOTE: ProcessAnswer(exit_code=exit_code)})
                remote_branch = RemoteBranch(
                    repository=Path("/srv/shop"), branch="integration/shop_w2", environment=FORGE_ENVIRONMENT
                )

                # Act
                found = find_remote_branch(git, remote_branch)

                # Assert
                self.assertEqual(found, expected)

    def test_should_ask_the_remote_with_the_environment_of_the_forge(self):
        # Arrange
        git = RecordingProcessRunner()
        remote_branch = RemoteBranch(
            repository=Path("/srv/shop"), branch="integration/shop_w2", environment=FORGE_ENVIRONMENT
        )

        # Act
        find_remote_branch(git, remote_branch)

        # Assert
        [asked] = git.requests
        self.assertEqual(asked.argv, LS_REMOTE)
        self.assertEqual(asked.cwd, "/srv/shop")
        self.assertEqual(asked.environment, FORGE_ENVIRONMENT)
