import os
import tempfile
import unittest
from pathlib import Path

from brigade.git.read_worktree_state import ChangedFile, WorktreeState, read_worktree_state
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

TOPLEVEL_AND_HEAD = ("git", "rev-parse", "--show-toplevel", "HEAD")
STATUS = ("git", "status", "--porcelain", "-z", "--no-renames", "--untracked-files=all")
HEAD = "5ff69cd0a1b2c3d4e5f60718293a4b5c6d7e8f90"
MTIME_NS = 1793559404642000000


class ReadWorktreeStateTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.worktree = Path(directory.name)

    def _write(self, name: str, text: str) -> None:
        path = self.worktree / name
        path.write_text(text, encoding="utf-8")
        os.utime(path, ns=(MTIME_NS, MTIME_NS))

    def _answer(self, status: str) -> RecordingProcessRunner:
        return RecordingProcessRunner(
            {
                TOPLEVEL_AND_HEAD: ProcessAnswer(stdout=f"{self.worktree}\n{HEAD}\n"),
                STATUS: ProcessAnswer(stdout=status),
            }
        )

    def test_should_read_the_head_and_the_size_and_mtime_of_each_changed_file(self):
        # Arrange
        self._write("cli.py", "print('hour')\n")
        git = self._answer(" M cli.py\0")

        # Act
        state = read_worktree_state(git, self.worktree, Path("/state/runs/r1/progress.awawa"))

        # Assert
        self.assertEqual(
            state,
            WorktreeState(head=HEAD, changed=frozenset({ChangedFile(path="cli.py", size=14, mtime_ns=MTIME_NS)})),
        )

    def test_should_leave_the_progress_file_out(self):
        # Arrange
        self._write("progress.awawa", "ENTRY e1\n")
        git = self._answer("?? progress.awawa\0")

        # Act
        state = read_worktree_state(git, self.worktree, self.worktree / "progress.awawa")

        # Assert
        self.assertEqual(state, WorktreeState(head=HEAD, changed=frozenset()))

    def test_should_read_no_size_of_a_deleted_file(self):
        # Arrange
        git = self._answer(" D notes.md\0")

        # Act
        state = read_worktree_state(git, self.worktree, Path("/state/runs/r1/progress.awawa"))

        # Assert
        self.assertEqual(
            state,
            WorktreeState(head=HEAD, changed=frozenset({ChangedFile(path="notes.md", size=None, mtime_ns=None)})),
        )

    def test_should_read_no_state_of_a_directory_that_is_no_git_work_tree(self):
        # Arrange
        git = RecordingProcessRunner({TOPLEVEL_AND_HEAD: ProcessAnswer(exit_code=128)})

        # Act
        state = read_worktree_state(git, self.worktree, Path("/state/runs/r1/progress.awawa"))

        # Assert
        self.assertIsNone(state)
