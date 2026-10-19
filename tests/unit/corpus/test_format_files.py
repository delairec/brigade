import unittest
from pathlib import Path

from brigade.corpus.format_files import format_files
from tests.unit.recording_process_runner import RecordingProcessRunner


class FormatFilesTest(unittest.TestCase):
    def test_should_format_the_files_from_the_directory_of_the_first(self):
        # Arrange
        awawa = RecordingProcessRunner()

        # Act
        format_files(awawa, (Path("/srv/shop/corpus/tasks.awawa"), Path("/srv/shop/corpus/rules.awawa")))

        # Assert
        self.assertEqual(
            awawa.commands,
            [
                (
                    "/srv/shop/corpus",
                    ("awawa", "fmt", "/srv/shop/corpus/tasks.awawa", "/srv/shop/corpus/rules.awawa"),
                )
            ],
        )
