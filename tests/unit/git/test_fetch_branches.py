import unittest
from pathlib import Path

from brigade.git.fetch_branches import BranchesFetch, fetch_branches
from brigade.system.run_process import ProcessRequest
from tests.unit.recording_process_runner import RecordingProcessRunner


class FetchBranchesTest(unittest.TestCase):
    def test_should_fetch_the_branches_from_origin_under_the_account_environment(self):
        # Arrange
        git = RecordingProcessRunner()
        account = {"GH_TOKEN": "bot-token"}

        # Act
        fetch_branches(
            git, BranchesFetch(repository=Path("/srv/shop"), branches=("main", "feat/b42"), environment=account)
        )

        # Assert
        self.assertEqual(
            git.requests,
            [
                ProcessRequest(
                    argv=("git", "fetch", "--quiet", "origin", "main", "feat/b42"),
                    cwd="/srv/shop",
                    timeout_s=120.0,
                    environment={"GH_TOKEN": "bot-token"},
                )
            ],
        )
