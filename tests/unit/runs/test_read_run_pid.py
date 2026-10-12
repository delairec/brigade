import tempfile
import unittest
from pathlib import Path

from brigade.runs.read_run_pid import read_run_pid


class ReadRunPidTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.run_directory = Path(directory.name)

    def test_should_read_the_pid_and_the_identity_of_the_process_the_run_wrote(self):
        # Arrange
        (self.run_directory / "pid").write_text("4242 987654 0f2a4c6e-1b3d-4f5a-8c7e-9d0b2a4c6e8f\n")

        # Act
        recorded = read_run_pid(self.run_directory)

        # Assert
        self.assertEqual(recorded, (4242, "987654 0f2a4c6e-1b3d-4f5a-8c7e-9d0b2a4c6e8f"))

    def test_should_read_no_pid_before_the_run_wrote_one(self):
        # Act
        recorded = read_run_pid(self.run_directory)

        # Assert
        self.assertIsNone(recorded)

    def test_should_read_no_pid_from_a_file_not_of_the_form_pid_start_time_boot_id(self):
        # Arrange
        rows = [
            ("an empty file", "\n"),
            ("the pid alone, written before the identity", "4242\n"),
            ("a pid that is no number", "pid 987654 0f2a4c6e-1b3d-4f5a-8c7e-9d0b2a4c6e8f\n"),
            ("a start time that is no number", "4242 start 0f2a4c6e-1b3d-4f5a-8c7e-9d0b2a4c6e8f\n"),
            ("a fourth field", "4242 987654 0f2a4c6e-1b3d-4f5a-8c7e-9d0b2a4c6e8f extra\n"),
        ]
        for case, written in rows:
            with self.subTest(case=case):
                # Arrange
                (self.run_directory / "pid").write_text(written)

                # Act
                recorded = read_run_pid(self.run_directory)

                # Assert
                self.assertIsNone(recorded)
