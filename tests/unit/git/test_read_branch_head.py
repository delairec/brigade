import unittest
from pathlib import Path

from brigade.git.read_branch_head import read_branch_head
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

VERIFY_BRANCH = ("git", "rev-parse", "--verify", "--quiet", "refs/heads/integration/tides")


class ReadBranchHeadTest(unittest.TestCase):
    def test_should_read_the_head_of_the_local_branch(self):
        # Arrange
        git = RecordingProcessRunner({VERIFY_BRANCH: ProcessAnswer(stdout="5ff69cd\n")})

        # Act
        head = read_branch_head(git, Path("/srv/shop"), "integration/tides")

        # Assert
        self.assertEqual(head, "5ff69cd")

    def test_should_read_no_head_of_a_branch_that_does_not_stand_locally(self):
        # Arrange
        git = RecordingProcessRunner({VERIFY_BRANCH: ProcessAnswer(exit_code=1)})

        # Act
        head = read_branch_head(git, Path("/srv/shop"), "integration/tides")

        # Assert
        self.assertIsNone(head)

    def test_should_ask_git_in_the_repository(self):
        # Arrange
        git = RecordingProcessRunner({VERIFY_BRANCH: ProcessAnswer(stdout="5ff69cd\n")})

        # Act
        read_branch_head(git, Path("/srv/shop"), "integration/tides")

        # Assert
        self.assertEqual(git.commands, [("/srv/shop", VERIFY_BRANCH)])
