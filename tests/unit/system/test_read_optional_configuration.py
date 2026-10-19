import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.system.read_configuration import Configuration
from brigade.system.read_optional_configuration import read_optional_configuration


class ReadOptionalConfigurationTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)

    def test_should_read_the_configuration_file_when_written(self):
        # Arrange
        configuration_file = self.root / "config.toml"
        configuration_file.write_text('client = "fake"\n')

        # Act
        configuration = read_optional_configuration(configuration_file)

        # Assert
        self.assertEqual(configuration, Configuration(client="fake"))

    def test_should_answer_nothing_configured_without_a_file(self):
        # Act
        configuration = read_optional_configuration(self.root / "config.toml")

        # Assert
        self.assertEqual(configuration, Configuration())
