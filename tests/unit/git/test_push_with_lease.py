import unittest
from pathlib import Path

from brigade.git.push_with_lease import LeasedPush, push_with_lease
from brigade.system.run_process import ProcessRequest
from tests.unit.recording_process_runner import RecordingProcessRunner


class PushWithLeaseTest(unittest.TestCase):
    def test_should_push_the_head_onto_the_branch_only_while_the_remote_holds_the_expected_head(self):
        # Arrange
        git = RecordingProcessRunner()
        account = {"GH_TOKEN": "bot-token"}

        # Act
        push_with_lease(
            git,
            LeasedPush(worktree=Path("/srv/shop"), branch="feat/b42", expected_head="8885daa", environment=account),
        )

        # Assert
        self.assertEqual(
            git.requests,
            [
                ProcessRequest(
                    argv=("git", "push", "--quiet", "--force-with-lease=feat/b42:8885daa", "origin", "HEAD:feat/b42"),
                    cwd="/srv/shop",
                    timeout_s=120.0,
                    environment={"GH_TOKEN": "bot-token"},
                )
            ],
        )
