import unittest
from pathlib import Path

from brigade.git.list_tracked_files import list_tracked_files
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner


class ListTrackedFilesTest(unittest.TestCase):
    def test_should_list_the_tracked_files_matching_the_pathspec(self):
        # Arrange
        git = RecordingProcessRunner(
            {
                ("git", "ls-files", "-z", "--", "*.awawa"): ProcessAnswer(
                    stdout="corpus/tasks.awawa\0corpus/rules.awawa\0"
                )
            }
        )

        # Act
        files = list_tracked_files(git, Path("/srv/shop"), "*.awawa")

        # Assert
        self.assertEqual(files, ("corpus/tasks.awawa", "corpus/rules.awawa"))
