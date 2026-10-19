import tempfile
import unittest
from pathlib import Path

from brigade.errors import CannotWrite
from brigade.system.write_text_file import write_text_file


class WriteTextFileTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.path = Path(self.root.name) / "brigade.timer"

    def test_should_write_the_text(self):
        # Act
        write_text_file(self.path, "[Timer]\nOnCalendar=*:0/5\n")

        # Assert
        self.assertEqual(self.path.read_text(encoding="utf-8"), "[Timer]\nOnCalendar=*:0/5\n")

    def test_should_replace_the_previous_text(self):
        # Arrange
        self.path.write_text("[Timer]\nOnCalendar=hourly\n")

        # Act
        write_text_file(self.path, "[Timer]\nOnCalendar=*:0/5\n")

        # Assert
        self.assertEqual(self.path.read_text(encoding="utf-8"), "[Timer]\nOnCalendar=*:0/5\n")

    def test_should_name_the_directory_standing_where_the_file_goes(self):
        # Arrange
        self.path.mkdir()

        # Act
        with self.assertRaises(CannotWrite) as refusal:
            write_text_file(self.path, "[Timer]\n")

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot write {self.path}: Is a directory")


class WriteTextFileWhereTheMachineRefusesTheWriteTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.units = Path(self.root.name) / "units"

    def test_should_name_the_file_it_cannot_create(self):
        # Arrange
        self.units.touch()

        # Act
        with self.assertRaises(CannotWrite) as refusal:
            write_text_file(self.units / "brigade.timer", "[Timer]\n")

        # Assert
        self.assertEqual(str(refusal.exception), f"cannot write {self.units / 'brigade.timer'}: Not a directory")
