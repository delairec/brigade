import tempfile
import unittest
from pathlib import Path

from brigade.git.detect_repository import detect_repository
from brigade.system.run_process import ProcessRecord


def record_of(exit_code: int) -> ProcessRecord:
    return ProcessRecord(argv=("git",), cwd="/", exit_code=exit_code, stdout="", stderr="")


class DetectRepositoryTest(unittest.TestCase):
    def test_should_return_false_when_the_path_is_not_a_directory(self):
        # Arrange
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        path = Path(root.name) / "missing"

        # Act
        result = detect_repository(lambda request: record_of(0), path)

        # Assert
        self.assertFalse(result)

    def test_should_return_true_when_git_recognises_the_directory(self):
        # Arrange
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        path = Path(root.name)

        # Act
        result = detect_repository(lambda request: record_of(0), path)

        # Assert
        self.assertTrue(result)

    def test_should_return_false_when_git_does_not_recognise_the_directory(self):
        # Arrange
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        path = Path(root.name)

        # Act
        result = detect_repository(lambda request: record_of(128), path)

        # Assert
        self.assertFalse(result)
