import unittest
from pathlib import Path

from brigade.git.push_branch import BranchPush
from brigade.git.push_branch_with_lease import push_branch_with_lease
from brigade.system.run_process import ProcessRequest
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

READ_ORIGIN_HEAD = ("git", "rev-parse", "--verify", "--quiet", "refs/remotes/origin/fix/B12-the-parser")
ABSENT = 1


class PushBranchWithLeaseTest(unittest.TestCase):
    def test_should_push_the_branch_with_the_lease_of_the_head_of_origin_it_read(self):
        # Arrange
        git = RecordingProcessRunner({READ_ORIGIN_HEAD: ProcessAnswer(stdout="c0ffee\n")})
        account = {"GH_TOKEN": "bot-token"}

        # Act
        push_branch_with_lease(
            git, BranchPush(repository=Path("/srv/oak-b12"), branch="fix/B12-the-parser", environment=account)
        )

        # Assert
        self.assertEqual(
            git.requests[-1],
            ProcessRequest(
                argv=(
                    "git",
                    "push",
                    "--quiet",
                    "--force-with-lease=fix/B12-the-parser:c0ffee",
                    "origin",
                    "fix/B12-the-parser",
                ),
                cwd="/srv/oak-b12",
                timeout_s=120.0,
                environment={"GH_TOKEN": "bot-token"},
            ),
        )

    def test_should_push_a_branch_absent_from_origin_with_the_lease_that_it_is_absent(self):
        # Arrange
        git = RecordingProcessRunner({READ_ORIGIN_HEAD: ProcessAnswer(exit_code=ABSENT)})
        no_account = {}

        # Act
        push_branch_with_lease(
            git, BranchPush(repository=Path("/srv/oak-b12"), branch="fix/B12-the-parser", environment=no_account)
        )

        # Assert
        self.assertEqual(
            git.requests[-1].argv,
            ("git", "push", "--quiet", "--force-with-lease=fix/B12-the-parser:", "origin", "fix/B12-the-parser"),
        )
