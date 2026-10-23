import tempfile
import unittest
from pathlib import Path

from brigade.system.parse_configuration import Configuration, ConfigurationMissing
from brigade.system.read_configuration import CONFIGURATION_OPTIONAL, CONFIGURATION_REQUIRED, read_configuration
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

CONFIGURATION_FILE = "config.toml"


class ReadConfigurationTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "config").mkdir()

    def test_should_read_the_configuration_file_when_written(self):
        # Arrange
        (self.root / "config" / CONFIGURATION_FILE).write_text('client = "fake"\n', encoding="utf-8")
        for request in [CONFIGURATION_REQUIRED, CONFIGURATION_OPTIONAL]:
            with self.subTest(request=request):
                # Act
                configuration = read_configuration(create_test_runtime(create_test_paths(self.root)), request)

                # Assert
                self.assertEqual(configuration, Configuration(client="fake"))

    def test_should_answer_nothing_configured_when_the_file_is_optional_and_missing(self):
        # Act
        configuration = read_configuration(create_test_runtime(create_test_paths(self.root)), CONFIGURATION_OPTIONAL)

        # Assert
        self.assertEqual(configuration, Configuration())

    def test_should_refuse_a_missing_file_when_the_configuration_is_required(self):
        # Arrange
        configuration_path = self.root / "config" / CONFIGURATION_FILE

        # Act
        with self.assertRaises(ConfigurationMissing) as raised:
            read_configuration(create_test_runtime(create_test_paths(self.root)), CONFIGURATION_REQUIRED)

        # Assert
        self.assertEqual(str(raised.exception), f"no configuration at {configuration_path}; run brigade init")
