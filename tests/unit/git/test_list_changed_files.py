import unittest
from pathlib import Path

from brigade.git.list_changed_files import list_changed_files
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner


class ListChangedFilesTest(unittest.TestCase):
    def test_should_list_the_modified_and_untracked_files(self):
        # Arrange
        git = RecordingProcessRunner(
            {
                ("git", "status", "--porcelain", "-z", "--no-renames", "--untracked-files=all"): ProcessAnswer(
                    stdout=" M brigade/cli.py\0?? notes.md\0"
                )
            }
        )

        # Act
        changed = list_changed_files(git, Path("/srv/shop"))

        # Assert
        self.assertEqual(changed, ("brigade/cli.py", "notes.md"))
