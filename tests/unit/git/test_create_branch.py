import unittest
from pathlib import Path

from brigade.git.create_branch import create_branch
from tests.unit.recording_process_runner import RecordingProcessRunner


class CreateBranchTest(unittest.TestCase):
    def test_should_switch_the_worktree_to_a_new_branch(self):
        # Arrange
        git = RecordingProcessRunner()

        # Act
        create_branch(git, Path("/srv/worktrees/b42"), "feat/b42")

        # Assert
        self.assertEqual(git.commands, [("/srv/worktrees/b42", ("git", "switch", "--quiet", "--create", "feat/b42"))])
