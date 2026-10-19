import unittest

from brigade.git.read_git_version import read_git_version
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner


class ReadGitVersionTest(unittest.TestCase):
    def test_should_answer_the_bare_version_number(self):
        # Arrange
        git = RecordingProcessRunner(
            {("git", "--version"): ProcessAnswer(stdout="git version 2.39.5 (Apple Git-154)\n")}
        )

        # Act
        version = read_git_version(git)

        # Assert
        self.assertEqual(version, "2.39.5")
