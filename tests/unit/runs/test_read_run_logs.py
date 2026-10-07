import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.runs.read_run_logs import read_run_logs
from brigade.runs.run_locations import RUN_RECORD_FILE, SEGMENTS_DIRECTORY, STDERR_FILE, STDOUT_FILE


class ReadRunLogsTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.state_root = Path(self.root.name)
        self.run_directory = self.state_root / "runs" / "20261007T120000Z-abcdef"
        self.run_directory.mkdir(parents=True)
        (self.run_directory / RUN_RECORD_FILE).write_text("{}")

    def tearDown(self):
        self.root.cleanup()

    def test_should_refuse_a_run_id_with_a_path_separator(self):
        # Act
        with self.assertRaises(BrigadeError) as raised:
            read_run_logs(self.state_root, "../escape", None)

        # Assert
        self.assertEqual(str(raised.exception), "no run ../escape")

    def test_should_refuse_a_run_that_does_not_exist(self):
        # Act
        with self.assertRaises(BrigadeError) as raised:
            read_run_logs(self.state_root, "20261007T120000Z-fedcba", None)

        # Assert
        self.assertEqual(str(raised.exception), "no run 20261007T120000Z-fedcba")

    def test_should_return_an_empty_list_when_there_are_no_segments(self):
        # Act
        lines = read_run_logs(self.state_root, "20261007T120000Z-abcdef", None)

        # Assert
        self.assertEqual(lines, [])

    def test_should_read_the_logs_of_every_segment_in_order(self):
        # Arrange
        segments = self.run_directory / SEGMENTS_DIRECTORY
        (segments / "1").mkdir(parents=True)
        (segments / "2").mkdir(parents=True)
        (segments / "1" / STDOUT_FILE).write_text("first out\n")
        (segments / "1" / STDERR_FILE).write_text("first err\n")
        (segments / "2" / STDOUT_FILE).write_text("second out\n")
        (segments / "2" / STDERR_FILE).write_text("second err\n")

        # Act
        lines = read_run_logs(self.state_root, "20261007T120000Z-abcdef", None)

        # Assert
        self.assertEqual(lines, ["first out", "first err", "second out", "second err"])

    def test_should_return_only_the_last_lines_when_a_tail_is_given(self):
        # Arrange
        segments = self.run_directory / SEGMENTS_DIRECTORY
        (segments / "1").mkdir(parents=True)
        (segments / "1" / STDOUT_FILE).write_text("line 1\nline 2\nline 3\n")

        # Act
        lines = read_run_logs(self.state_root, "20261007T120000Z-abcdef", 2)

        # Assert
        self.assertEqual(lines, ["line 2", "line 3"])

    def test_should_skip_a_segment_directory_whose_name_is_not_a_number(self):
        # Arrange
        segments = self.run_directory / SEGMENTS_DIRECTORY
        (segments / "abc").mkdir(parents=True)
        (segments / "abc" / STDOUT_FILE).write_text("ignored\n")
        (segments / "1").mkdir(parents=True)
        (segments / "1" / STDOUT_FILE).write_text("kept\n")

        # Act
        lines = read_run_logs(self.state_root, "20261007T120000Z-abcdef", None)

        # Assert
        self.assertEqual(lines, ["kept"])
