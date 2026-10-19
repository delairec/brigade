import unittest
from pathlib import Path

from brigade.git.force_push_branch import force_push_branch
from tests.unit.recording_process_runner import RecordingProcessRunner


class ForcePushBranchTest(unittest.TestCase):
    def test_should_push_the_branch_to_origin_by_force(self):
        # Arrange
        git = RecordingProcessRunner()

        # Act
        force_push_branch(git, Path("/srv/shop"), "feat/b42")

        # Assert
        self.assertEqual(git.commands, [("/srv/shop", ("git", "push", "--quiet", "--force", "origin", "feat/b42"))])
