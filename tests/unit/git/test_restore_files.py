import unittest
from pathlib import Path

from brigade.git.restore_files import restore_files
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner


class RestoreFilesHeldAtHeadTest(unittest.TestCase):
    def test_should_check_the_files_out_of_head(self):
        # Arrange
        git = RecordingProcessRunner(
            {("git", "ls-tree", "--name-only", "HEAD", "--", "tasks.awawa"): ProcessAnswer(stdout="tasks.awawa\n")}
        )

        # Act
        restore_files(git, Path("/srv/shop"), ("tasks.awawa",))

        # Assert
        self.assertEqual(git.commands[1:], [("/srv/shop", ("git", "checkout", "HEAD", "--", "tasks.awawa"))])


class RestoreFilesNewSinceHeadTest(unittest.TestCase):
    def test_should_unstage_and_delete_the_files(self):
        # Arrange
        git = RecordingProcessRunner()

        # Act
        restore_files(git, Path("/srv/shop"), ("new.awawa",))

        # Assert
        self.assertEqual(
            git.commands[1:],
            [
                ("/srv/shop", ("git", "rm", "--cached", "--quiet", "--ignore-unmatch", "--", "new.awawa")),
                ("/srv/shop", ("git", "clean", "--force", "--quiet", "--", "new.awawa")),
            ],
        )
