import unittest
from pathlib import Path

from brigade.git.has_local_changes import has_local_changes
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner


class HasLocalChangesTest(unittest.TestCase):
    def test_should_tell_whether_the_worktree_holds_changes_a_removal_would_lose(self):
        for case, status, expected in [
            ("a modified tracked file", " M brigade/cli.py\n", True),
            ("a staged tracked file", "M  brigade/cli.py\n", True),
            ("an untracked file", "?? notes/draft.md\n", True),
            ("no change", "", False),
        ]:
            with self.subTest(case=case):
                # Arrange
                git = RecordingProcessRunner({("git", "status", "--porcelain"): ProcessAnswer(stdout=status)})

                # Act
                local = has_local_changes(git, Path("/srv/shop/.brigade/worktrees/S3"))

                # Assert
                self.assertEqual(local, expected)

    def test_should_run_git_status_in_the_worktree(self):
        # Arrange
        git = RecordingProcessRunner()

        # Act
        has_local_changes(git, Path("/srv/shop/.brigade/worktrees/S3"))

        # Assert
        self.assertEqual(git.commands, [("/srv/shop/.brigade/worktrees/S3", ("git", "status", "--porcelain"))])
