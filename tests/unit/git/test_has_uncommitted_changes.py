import unittest
from pathlib import Path

from brigade.git.has_uncommitted_changes import has_uncommitted_changes
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner


class HasUncommittedChangesTest(unittest.TestCase):
    def test_should_tell_whether_the_worktree_holds_changes_to_its_tracked_files(self):
        for case, status, expected in [
            ("a modified tracked file", " M brigade/cli.py\n", True),
            ("a staged tracked file", "M  brigade/cli.py\n", True),
            ("no change to a tracked file", "", False),
        ]:
            with self.subTest(case=case):
                # Arrange
                git = RecordingProcessRunner(
                    {("git", "status", "--porcelain", "--untracked-files=no"): ProcessAnswer(stdout=status)}
                )

                # Act
                uncommitted = has_uncommitted_changes(git, Path("/srv/shop/.brigade/worktrees/S3"))

                # Assert
                self.assertEqual(uncommitted, expected)
