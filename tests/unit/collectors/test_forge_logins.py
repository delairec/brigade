import tempfile
import unittest
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collectors.forge_logins import collect
from brigade.system.parse_configuration import Configuration
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

ENVIRONMENT = {"BRIGADE_PROJECT_PATH": "/srv/shop", "BRIGADE_SINCE": "1970-01-01", "BRIGADE_PARAMS": "{}"}
BOUND_LOGINS = Configuration(forge_accounts={"build": "clauche-bot", "cli": "clauche-bot", "review": "prudence-bot"})
NO_FORGE_PLUGIN = None


class TokenOfClaucheBotForgeDouble:
    def read_login_environment(self, request: dict, runtime) -> dict:
        environment = {"GH_TOKEN": "gho_clauche"} if request["login"] == "clauche-bot" else None
        return {"schema_version": 1, "environment": environment}


class ForgeLoginsCollectorTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.runtime = create_test_runtime(create_test_paths(Path(directory.name)))

    def test_should_tell_of_each_bound_login_whether_gh_prints_its_token(self):
        # Arrange
        equipment = CollectorEquipment(
            configuration=BOUND_LOGINS, forge=TokenOfClaucheBotForgeDouble(), forge_name="github", resolve_client=None
        )

        # Act
        document = collect(ENVIRONMENT, self.runtime, equipment)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "collector": "forge-logins",
                "collected_at": "2026-10-19T09:00:00Z",
                "cache": False,
                "summary": {
                    "logins": [
                        {"login": "clauche-bot", "keys": ["build", "cli"], "token": True},
                        {"login": "prudence-bot", "keys": ["review"], "token": False},
                    ]
                },
                "items": [],
            },
        )

    def test_should_collect_no_login_for_a_project_on_no_forge(self):
        # Arrange
        equipment = CollectorEquipment(
            configuration=BOUND_LOGINS, forge=NO_FORGE_PLUGIN, forge_name="none", resolve_client=None
        )

        # Act
        document = collect(ENVIRONMENT, self.runtime, equipment)

        # Assert
        self.assertEqual(document["summary"], {"logins": []})
