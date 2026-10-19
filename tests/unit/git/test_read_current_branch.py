import unittest
from pathlib import Path

from brigade.git.read_current_branch import read_current_branch
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner


class ReadCurrentBranchTest(unittest.TestCase):
    def test_should_answer_the_branch_checked_out(self):
        # Arrange
        git = RecordingProcessRunner({("git", "branch", "--show-current"): ProcessAnswer(stdout="feat/b42\n")})

        # Act
        branch = read_current_branch(git, Path("/srv/shop"))

        # Assert
        self.assertEqual(branch, "feat/b42")
