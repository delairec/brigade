import unittest
from pathlib import Path

from brigade.git.fetch_branches import BranchesFetch, fetch_branches
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
            [(request.argv, request.environment) for request in git.requests],
            [(("git", "fetch", "--quiet", "origin", "main", "feat/b42"), {"GH_TOKEN": "bot-token"})],
        )
