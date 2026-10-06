import os
import subprocess
import tempfile
import unittest
from pathlib import Path

CLONE_ENTRY_POINT = Path(__file__).resolve().parents[2] / "bin" / "brigade"


class BrigadeInstallWhenLinkedIntoADirectoryOnPathTest(unittest.TestCase):
    def setUp(self):
        self.path_directory = tempfile.TemporaryDirectory()
        self.unrelated_working_directory = tempfile.TemporaryDirectory()
        Path(self.path_directory.name, "brigade").symlink_to(CLONE_ENTRY_POINT)

    def tearDown(self):
        self.path_directory.cleanup()
        self.unrelated_working_directory.cleanup()

    def test_should_run_from_any_working_directory(self):
        # Arrange
        environment = dict(os.environ, PATH=self.path_directory.name + os.pathsep + os.environ["PATH"])

        # Act
        completed = subprocess.run(
            ["brigade", "--version"],  # noqa: S607 - the PATH lookup is the behaviour under test
            capture_output=True,
            text=True,
            cwd=self.unrelated_working_directory.name,
            env=environment,
            check=False,
        )

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, "brigade 0.1.0\n")
