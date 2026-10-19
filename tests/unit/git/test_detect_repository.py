import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.git.detect_repository import detect_repository
from brigade.system.run_process import ProcessRequest
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner


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


class DetectRepositoryOfADirectoryTest(unittest.TestCase):
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.directory)

    def test_should_answer_whether_git_finds_a_repository_there(self):
        for exit_code, expected in [(0, True), (128, False)]:
            with self.subTest(exit_code=exit_code):
                # Arrange
                git = RecordingProcessRunner(
                    {
                        ("git", "rev-parse", "--git-dir"): ProcessAnswer(
                            exit_code=exit_code, stderr="not a git repository"
                        )
                    }
                )

                # Act
                is_repository = detect_repository(git, self.directory)

                # Assert
                self.assertEqual(is_repository, expected)
