import tempfile
import unittest
from pathlib import Path

from brigade.commands._read_cli_login import read_cli_login
from brigade.system.parse_configuration import Configuration
from tests.unit.commands.create_plugin_resolver import create_plugin_resolver
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime


class AccountForgeDouble:
    def describe_account(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "login": "octo-cli"}


class ReadCliLoginTest(unittest.TestCase):
    def test_should_read_the_login_the_forge_answers_for_the_cli_key(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        runtime = create_test_runtime(
            create_test_paths(root), resolve_plugin=create_plugin_resolver({("forge", "github"): AccountForgeDouble()})
        )

        # Act
        login = read_cli_login(Configuration(), runtime)

        # Assert
        self.assertEqual(login, "octo-cli")
