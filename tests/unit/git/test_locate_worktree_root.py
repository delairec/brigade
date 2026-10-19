import unittest
from pathlib import Path

from brigade.git.locate_worktree_root import locate_worktree_root
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner


class LocateWorktreeRootTest(unittest.TestCase):
    def test_should_answer_the_top_level_of_the_worktree_holding_the_path(self):
        # Arrange
        git = RecordingProcessRunner(
            {("git", "rev-parse", "--show-toplevel"): ProcessAnswer(stdout="/srv/worktrees/b42\n")}
        )

        # Act
        root = locate_worktree_root(git, Path("/srv/worktrees/b42/brigade"))

        # Assert
        self.assertEqual(root, Path("/srv/worktrees/b42"))
