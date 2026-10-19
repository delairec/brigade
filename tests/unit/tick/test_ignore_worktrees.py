import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.tick.ignore_worktrees import ignore_worktrees
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

IGNORE_FILE = ("git", "cat-file", "-p", "integration/w1:.gitignore")
WORKTREES = ("git", "worktree", "list", "--porcelain", "-z")
HASH_OBJECT = ("git", "hash-object", "-w", "--stdin")


class IgnoreWorktreesAlreadyIgnoredTest(unittest.TestCase):
    def test_should_commit_nothing(self):
        # Arrange
        git = RecordingProcessRunner({IGNORE_FILE: ProcessAnswer(stdout="node_modules/\n.brigade/worktrees/\n")})

        # Act
        ignore_worktrees(git, Path("/srv/shop"), "integration/w1")

        # Assert
        self.assertEqual(git.commands, [("/srv/shop", IGNORE_FILE)])


class IgnoreWorktreesNotYetIgnoredTest(unittest.TestCase):
    def test_should_commit_the_ignore_file_with_the_worktrees_directory_added(self):
        # Arrange
        git = RecordingProcessRunner({IGNORE_FILE: ProcessAnswer(stdout="node_modules/\n")})

        # Act
        ignore_worktrees(git, Path("/srv/shop"), "integration/w1")

        # Assert
        self.assertEqual(
            [request.stdin for request in git.requests if request.argv == HASH_OBJECT],
            ["node_modules/\n.brigade/worktrees/\n"],
        )

    def test_should_refuse_a_wave_branch_checked_out_in_a_worktree(self):
        # Arrange
        git = RecordingProcessRunner(
            {WORKTREES: ProcessAnswer(stdout="worktree /srv/shop\0HEAD 4f2a9c1\0branch refs/heads/integration/w1\0\0")}
        )

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            ignore_worktrees(git, Path("/srv/shop"), "integration/w1")

        # Assert
        self.assertEqual(str(refusal.exception), "the wave branch integration/w1 is checked out in /srv/shop")
