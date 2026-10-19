import unittest
from pathlib import Path

from brigade.git.find_branch import find_branch
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

VERIFY_BRANCH = ("git", "rev-parse", "--verify", "--quiet", "refs/heads/feat/b42")


class FindBranchTest(unittest.TestCase):
    def test_should_tell_whether_the_local_branch_exists(self):
        for exit_code, expected in [(0, True), (1, False)]:
            with self.subTest(exit_code=exit_code):
                # Arrange
                git = RecordingProcessRunner({VERIFY_BRANCH: ProcessAnswer(exit_code=exit_code)})

                # Act
                found = find_branch(git, Path("/srv/shop"), "feat/b42")

                # Assert
                self.assertEqual(found, expected)
