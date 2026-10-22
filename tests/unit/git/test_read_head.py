import unittest
from pathlib import Path

from brigade.git.read_head import read_head
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner


class ReadHeadTest(unittest.TestCase):
    def test_should_give_the_commit_the_worktree_stands_on(self):
        # Arrange
        git = RecordingProcessRunner({("git", "rev-parse", "HEAD"): ProcessAnswer(stdout="9a9a9a9\n")})

        # Act
        head = read_head(git, Path("/srv/shop"))

        # Assert
        self.assertEqual(head, "9a9a9a9")
