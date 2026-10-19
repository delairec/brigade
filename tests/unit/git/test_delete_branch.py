import unittest
from pathlib import Path

from brigade.git.delete_branch import delete_branch
from tests.unit.recording_process_runner import RecordingProcessRunner


class DeleteBranchTest(unittest.TestCase):
    def test_should_delete_the_branch_even_unmerged(self):
        # Arrange
        git = RecordingProcessRunner()

        # Act
        delete_branch(git, Path("/srv/shop"), "feat/b42")

        # Assert
        self.assertEqual(git.commands, [("/srv/shop", ("git", "branch", "--quiet", "-D", "feat/b42"))])
