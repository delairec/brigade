import json
import tempfile
import unittest
from pathlib import Path

from brigade.system.process_trace import ProcessTrace
from brigade.system.trail_writer import TrailWriter

GIT_VERSION = ProcessTrace(("git", "--version"), "/", "exited", 0, 3)
AWAWA_LINT = ProcessTrace(("awawa", "lint"), "/", "exited", 1, 40)


class TrailWriterTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.destination = Path(self.root.name) / "commands" / "20261007T120000Z-doctor.jsonl"
        self.reported = []
        self.trail = TrailWriter(self.reported.append)

    def read_lines(self) -> list:
        return [json.loads(line) for line in self.destination.read_text().splitlines()]


class TrailWriterLocatedTest(TrailWriterTestCase):
    def test_should_create_the_trail_before_any_record(self):
        # Act
        self.trail.locate(self.destination)

        # Assert
        self.assertEqual(self.destination.read_text(), "")

    def test_should_append_one_line_per_record(self):
        # Arrange
        self.trail.locate(self.destination)

        # Act
        self.trail.append(GIT_VERSION)

        # Assert
        self.assertEqual(
            self.read_lines(),
            [
                {
                    "schema_version": 1,
                    "argv": ["git", "--version"],
                    "cwd": "/",
                    "exit": 0,
                    "duration_ms": 3,
                    "outcome": "exited",
                }
            ],
        )

    def test_should_report_each_record_it_appends(self):
        # Arrange
        self.trail.locate(self.destination)

        # Act
        self.trail.append(GIT_VERSION)

        # Assert
        self.assertEqual(self.reported, [GIT_VERSION])


class TrailWriterNotYetLocatedTest(TrailWriterTestCase):
    def test_should_write_the_records_it_held_where_it_is_located_then(self):
        # Arrange
        self.trail.append(GIT_VERSION)
        self.trail.append(AWAWA_LINT)

        # Act
        self.trail.locate(self.destination)

        # Assert
        self.assertEqual([line["argv"] for line in self.read_lines()], [["git", "--version"], ["awawa", "lint"]])

    def test_should_settle_the_records_it_held_on_the_fallback(self):
        # Arrange
        self.trail.append(GIT_VERSION)

        # Act
        self.trail.settle(self.destination)

        # Assert
        self.assertEqual([line["argv"] for line in self.read_lines()], [["git", "--version"]])

    def test_should_settle_nothing_when_it_held_no_record(self):
        # Act
        self.trail.settle(self.destination)

        # Assert
        self.assertFalse(self.destination.exists())


class TrailWriterAlreadyLocatedTest(TrailWriterTestCase):
    def test_should_keep_its_trail_when_settled(self):
        # Arrange
        fallback = self.destination.with_name("20261007T120000Z-run.jsonl")
        self.trail.locate(self.destination)
        self.trail.append(GIT_VERSION)

        # Act
        self.trail.settle(fallback)

        # Assert
        self.assertEqual((len(self.read_lines()), fallback.exists()), (1, False))
