import unittest
from pathlib import Path

from brigade.git.read_origin_url import read_origin_url
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

GET_URL = ("git", "remote", "get-url", "origin")


class ReadOriginUrlTest(unittest.TestCase):
    def test_should_answer_the_url_of_origin(self):
        # Arrange
        git = RecordingProcessRunner({GET_URL: ProcessAnswer(stdout="git@github.com:ada/shop.git\n")})

        # Act
        url = read_origin_url(git, Path("/srv/shop"))

        # Assert
        self.assertEqual(url, "git@github.com:ada/shop.git")

    def test_should_answer_none_for_a_repository_without_origin(self):
        # Arrange
        git = RecordingProcessRunner({GET_URL: ProcessAnswer(exit_code=2, stderr="error: No such remote 'origin'")})

        # Act
        url = read_origin_url(git, Path("/srv/shop"))

        # Assert
        self.assertIsNone(url)
