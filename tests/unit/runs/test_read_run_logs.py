import tempfile
import unittest
from pathlib import Path

from brigade.runs.read_run_logs import read_run_logs

RUN_ID = "20261007T090000Z-b70a01"
WHOLE_LOG = None


class ReadRunLogsTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.state_root = Path(self.root.name) / "brigade"
        self.run_directory = self.state_root / "runs" / RUN_ID
        self.run_directory.mkdir(parents=True)
        (self.run_directory / "run.json").write_text("{}")

    def tearDown(self):
        self.root.cleanup()


class ReadRunLogsBeforeTheFirstSegmentTest(ReadRunLogsTestCase):
    def test_should_read_no_line(self):
        # Act
        lines = read_run_logs(self.state_root, RUN_ID, WHOLE_LOG)

        # Assert
        self.assertEqual(lines, [])


class ReadRunLogsOfASegmentThatWroteNoErrorTest(ReadRunLogsTestCase):
    def test_should_read_its_output_alone(self):
        # Arrange
        segment = self.run_directory / "segments" / "1"
        segment.mkdir(parents=True)
        (segment / "stdout.log").write_text("step 1 done\nstep 2 done\n")

        # Act
        lines = read_run_logs(self.state_root, RUN_ID, WHOLE_LOG)

        # Assert
        self.assertEqual(lines, ["step 1 done", "step 2 done"])
