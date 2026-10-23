import tempfile
import unittest
from pathlib import Path

from brigade.errors import CannotWrite
from brigade.system.append_line import append_line


class AppendLineTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.ledger = Path(self.root.name) / "ledger" / "2026-10.jsonl"

    def test_should_create_the_file_and_its_directory_with_the_line(self):
        # Act
        append_line(self.ledger, '{"event": "run.started"}')

        # Assert
        self.assertEqual(self.ledger.read_text(encoding="utf-8"), '{"event": "run.started"}\n')

    def test_should_keep_the_lines_already_written(self):
        # Arrange
        self.ledger.parent.mkdir()
        self.ledger.write_text('{"event": "run.started"}\n', encoding="utf-8")

        # Act
        append_line(self.ledger, '{"event": "run.finished"}')

        # Assert
        self.assertEqual(
            self.ledger.read_text(encoding="utf-8"), '{"event": "run.started"}\n{"event": "run.finished"}\n'
        )

    def test_should_name_the_file_it_cannot_write_where_a_file_stands_for_its_directory(self):
        # Arrange
        self.ledger.parent.touch()

        # Act
        with self.assertRaises(CannotWrite) as refusal:
            append_line(self.ledger, '{"event": "run.started"}')

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot write {self.ledger.parent}: File exists")
