import unittest
from pathlib import Path

from brigade.git.detect_repository import detect_repository
from brigade.system.run_process import ProcessRequest


def refuse_to_run(request: ProcessRequest):
    raise AssertionError(f"{' '.join(request.argv)} should not run")


class DetectRepositoryOfAMissingDirectoryTest(unittest.TestCase):
    def test_should_answer_no_repository_without_asking_git(self):
        # Arrange
        missing_directory = Path("/nonexistent/brigade/project")

        # Act
        is_repository = detect_repository(refuse_to_run, missing_directory)

        # Assert
        self.assertFalse(is_repository)
