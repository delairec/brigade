import unittest
from pathlib import Path

from brigade.git.create_repository import create_repository
from tests.unit.recording_process_runner import RecordingProcessRunner


class CreateRepositoryTest(unittest.TestCase):
    def test_should_initialise_a_repository_in_the_directory(self):
        # Arrange
        git = RecordingProcessRunner()

        # Act
        create_repository(git, Path("/home/ada/.config/brigade"))

        # Assert
        self.assertEqual(git.commands, [("/home/ada/.config/brigade", ("git", "init", "--quiet"))])
