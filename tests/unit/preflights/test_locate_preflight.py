import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.preflights.locate_preflight import locate_preflight


class LocatePreflightTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.preflights = Path(directory.name)

    def test_should_locate_the_file_of_the_preflight_named(self):
        # Arrange
        (self.preflights / "wave.toml").write_text("schema_version = 1\n")

        # Act
        file = locate_preflight("wave", self.preflights)

        # Assert
        self.assertEqual(file, self.preflights / "wave.toml")

    def test_should_refuse_a_name_no_preflight_carries_naming_it(self):
        # Act
        with self.assertRaises(BrigadeError) as raised:
            locate_preflight("wave", self.preflights)

        # Assert
        self.assertEqual(str(raised.exception), f"no preflight wave: no wave.toml in {self.preflights}")
