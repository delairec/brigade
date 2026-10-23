import unittest
from pathlib import Path

from brigade.git.force_push_branch import force_push_branch
from brigade.git.push_branch import BranchPush
from brigade.system.run_process import ProcessRequest
from tests.unit.recording_process_runner import RecordingProcessRunner


class ForcePushBranchTest(unittest.TestCase):
    def test_should_push_the_branch_to_origin_by_force_under_the_account_environment(self):
        # Arrange
        git = RecordingProcessRunner()
        account = {"GH_TOKEN": "bot-token"}

        # Act
        force_push_branch(git, BranchPush(repository=Path("/srv/shop"), branch="feat/b42", environment=account))

        # Assert
        self.assertEqual(
            git.requests,
            [
                ProcessRequest(
                    argv=("git", "push", "--quiet", "--force", "origin", "feat/b42"),
                    cwd="/srv/shop",
                    timeout_s=120.0,
                    environment={"GH_TOKEN": "bot-token"},
                )
            ],
        )
