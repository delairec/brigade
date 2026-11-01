import unittest
from pathlib import Path

from brigade.git.push_ref_to_branch import RefPush, push_ref_to_branch
from brigade.system.run_process import ProcessRequest
from tests.unit.recording_process_runner import RecordingProcessRunner


class PushRefToBranchTest(unittest.TestCase):
    def test_should_push_the_ref_to_the_branch_of_origin_under_the_account_environment(self):
        # Arrange
        git = RecordingProcessRunner()
        account = {"GH_TOKEN": "bot-token"}
        push = RefPush(
            repository=Path("/srv/shop"),
            ref="origin/main",
            branch="integration/milestone-integration-branch",
            environment=account,
        )

        # Act
        push_ref_to_branch(git, push)

        # Assert
        self.assertEqual(
            git.requests,
            [
                ProcessRequest(
                    argv=(
                        "git",
                        "push",
                        "--quiet",
                        "origin",
                        "origin/main:refs/heads/integration/milestone-integration-branch",
                    ),
                    cwd="/srv/shop",
                    timeout_s=120.0,
                    environment={"GH_TOKEN": "bot-token"},
                )
            ],
        )


if __name__ == "__main__":
    unittest.main()
