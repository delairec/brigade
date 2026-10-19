import unittest
from pathlib import Path

from brigade.git.push_branch import BranchPush, push_branch
from tests.unit.recording_process_runner import RecordingProcessRunner


class PushBranchTest(unittest.TestCase):
    def test_should_push_the_branch_to_origin_under_the_account_environment(self):
        # Arrange
        git = RecordingProcessRunner()
        account = {"GH_TOKEN": "bot-token"}

        # Act
        push_branch(git, BranchPush(repository=Path("/srv/shop"), branch="feat/b42", environment=account))

        # Assert
        self.assertEqual(
            [(request.argv, request.environment) for request in git.requests],
            [(("git", "push", "--quiet", "origin", "feat/b42"), {"GH_TOKEN": "bot-token"})],
        )
