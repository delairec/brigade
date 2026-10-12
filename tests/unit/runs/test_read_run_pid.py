import tempfile
import unittest
from pathlib import Path

from brigade.runs.read_run_pid import read_run_pid


class ReadRunPidTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.run_directory = Path(directory.name)

    def test_should_read_the_pid_the_run_wrote(self):
        # Arrange
        (self.run_directory / "pid").write_text("4242\n")

        # Act
        pid = read_run_pid(self.run_directory)

        # Assert
        self.assertEqual(pid, 4242)

    def test_should_read_no_pid_before_the_run_wrote_one(self):
        # Act
        pid = read_run_pid(self.run_directory)

        # Assert
        self.assertIsNone(pid)

    def test_should_read_no_pid_from_a_file_holding_no_number(self):
        for written in ["\n", "-4242\n", "pid\n"]:
            with self.subTest(written=written):
                # Arrange
                (self.run_directory / "pid").write_text(written)

                # Act
                pid = read_run_pid(self.run_directory)

                # Assert
                self.assertIsNone(pid)
