import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.system.read_text_file import read_text_file


class ReadTextFileTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.path = Path(self.root.name) / "verdict.json"

    def test_should_read_the_text(self):
        # Arrange
        self.path.write_text('{"verdict": "approve"}', encoding="utf-8")

        # Act
        text = read_text_file(self.path)

        # Assert
        self.assertEqual(text, '{"verdict": "approve"}')

    def test_should_name_the_file_it_cannot_read(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            read_text_file(self.path)

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot read {self.path}: No such file or directory")
