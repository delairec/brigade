import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.preflights.read_preflight_file import read_preflight_file

NIGHTLY = (
    "schema_version = 1\n"
    'name = "nightly"\n'
    'description = "the nightly checks of the shop"\n'
    'collectors = [{ name = "notes", parameters = { depth = "1" } }]\n'
    'checks = [{ name = "coverage" }]\n'
)


class ReadPreflightFileTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.directory = Path(self.root.name)

    def test_should_read_the_toml_file_named_after_the_preflight(self):
        # Arrange
        (self.directory / "nightly.toml").write_text(NIGHTLY)

        # Act
        preflight = read_preflight_file(self.directory, "nightly")

        # Assert
        self.assertEqual(
            preflight,
            {
                "schema_version": 1,
                "name": "nightly",
                "description": "the nightly checks of the shop",
                "collectors": [{"name": "notes", "parameters": {"depth": "1"}}],
                "checks": [{"name": "coverage"}],
            },
        )

    def test_should_hold_no_preflight_where_no_file_bears_its_name(self):
        # Act
        preflight = read_preflight_file(self.directory, "nightly")

        # Assert
        self.assertIsNone(preflight)

    def test_should_refuse_a_file_that_is_no_toml_document_naming_it(self):
        # Arrange
        (self.directory / "nightly.toml").write_text('name = "nightly\n')

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            read_preflight_file(self.directory, "nightly")

        # Assert
        self.assertRegex(
            str(refusal.exception), f"^the preflight file {self.directory / 'nightly.toml'} is no TOML document: "
        )
