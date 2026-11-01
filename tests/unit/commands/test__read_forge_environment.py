import tempfile
import unittest
from pathlib import Path

from brigade.commands._read_forge_environment import ForgeSlot, read_forge_environment
from brigade.system.parse_configuration import Configuration
from tests.unit.commands.create_plugin_resolver import create_plugin_resolver
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime


class LoginEnvironmentForgeDouble:
    def read_login_environment(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "environment": {"GH_TOKEN": "token-of-octo-build"}}


class ReadForgeEnvironmentTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.configuration = Configuration(forge_accounts={"build": "octo-build"})

    def test_should_read_the_login_environment_of_the_slot_from_the_forge_it_names(self):
        # Arrange
        runtime = create_test_runtime(
            create_test_paths(self.root),
            resolve_plugin=create_plugin_resolver({("forge", "github"): LoginEnvironmentForgeDouble()}),
        )

        # Act
        environment = read_forge_environment(self.configuration, ForgeSlot("github", "build"), runtime)

        # Assert
        self.assertEqual(environment, {"GH_TOKEN": "token-of-octo-build"})

    def test_should_read_no_login_environment_and_resolve_no_forge_for_a_project_of_forge_none(self):
        # Arrange
        no_forge_plugin = {}
        runtime = create_test_runtime(
            create_test_paths(self.root), resolve_plugin=create_plugin_resolver(no_forge_plugin)
        )

        # Act
        environment = read_forge_environment(self.configuration, ForgeSlot("none", "build"), runtime)

        # Assert
        self.assertEqual(environment, {})
