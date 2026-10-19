import unittest
from pathlib import Path

from brigade.git.read_file_at import read_file_at
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

SHOW_README = ("git", "cat-file", "-p", "4f2a9c1:README.md")


class ReadFileAtTest(unittest.TestCase):
    def test_should_answer_the_content_of_the_file_at_that_commit(self):
        # Arrange
        git = RecordingProcessRunner({SHOW_README: ProcessAnswer(stdout="# shop\n")})

        # Act
        content = read_file_at(git, Path("/srv/shop"), "4f2a9c1:README.md")

        # Assert
        self.assertEqual(content, "# shop\n")

    def test_should_answer_nothing_for_a_file_absent_at_that_commit(self):
        # Arrange
        git = RecordingProcessRunner({SHOW_README: ProcessAnswer(exit_code=128, stderr="fatal: path not in tree")})

        # Act
        content = read_file_at(git, Path("/srv/shop"), "4f2a9c1:README.md")

        # Assert
        self.assertEqual(content, "")
