import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.system.read_configuration import Configuration
from brigade.system.require_configured_client import ConfiguredClient, require_configured_client

CONFIGURATION_PATH = Path("/srv/config/brigade/config.toml")


class RequireConfiguredClientTest(unittest.TestCase):
    def test_should_name_the_client_the_configuration_sets(self):
        # Arrange
        configuration = Configuration(client="fake", scheduler="cron")

        # Act
        configured = require_configured_client(configuration, CONFIGURATION_PATH)

        # Assert
        self.assertEqual(
            configured, ConfiguredClient(name="fake", configuration=Configuration(client="fake", scheduler="cron"))
        )

    def test_should_refuse_a_configuration_that_names_no_client_naming_the_key_and_the_file(self):
        # Arrange
        configuration_without_client = Configuration(scheduler="cron")

        # Act
        with self.assertRaises(BrigadeError) as raised:
            require_configured_client(configuration_without_client, CONFIGURATION_PATH)

        # Assert
        self.assertEqual(
            str(raised.exception),
            "config.toml names no client: set the client key in /srv/config/brigade/config.toml",
        )
