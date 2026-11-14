import unittest
from pathlib import Path

from brigade.git.add_detached_worktree import DetachedWorktree, add_detached_worktree
from tests.unit.recording_process_runner import RecordingProcessRunner


class AddDetachedWorktreeTest(unittest.TestCase):
    def test_should_check_out_the_start_detached_in_a_new_worktree_locked_for_the_command_that_creates_it(self):
        # Arrange
        git = RecordingProcessRunner()
        worktree = DetachedWorktree(
            repository=Path("/srv/shop"), path=Path("/srv/worktrees/review"), start="4f2a9c1", reason="brigade run"
        )

        # Act
        add_detached_worktree(git, worktree)

        # Assert
        self.assertEqual(
            git.commands,
            [
                (
                    "/srv/shop",
                    (
                        "git",
                        "worktree",
                        "add",
                        "--quiet",
                        "--detach",
                        "--lock",
                        "--reason",
                        "brigade run",
                        "/srv/worktrees/review",
                        "4f2a9c1",
                    ),
                )
            ],
        )
