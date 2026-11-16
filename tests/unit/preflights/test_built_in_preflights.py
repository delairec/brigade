import tempfile
import unittest
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.preflights.run_preflight import BUILT_IN_PREFLIGHTS, PreflightRun, run_preflight
from brigade.system.parse_configuration import Configuration
from tests.unit.collectors.draft_processes import SHOP, script_draft_processes
from tests.unit.create_preflight_plugins import create_preflight_plugins
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

NO_PARAMETERS = {}
NO_FORGE_PLUGIN = None


class NoTokenForgeDouble:
    def read_login_environment(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "environment": None}


class BuiltInPreflightsTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.paths = create_test_paths(Path(directory.name))

    def run_built_in(self, name: str, parameters: dict, equipment: CollectorEquipment, runtime) -> list:
        run = PreflightRun(
            name=name,
            project=SHOP,
            parameters=parameters,
            equipment=equipment,
            preflights=BUILT_IN_PREFLIGHTS,
            plugins=create_preflight_plugins(self.paths),
        )
        return run_preflight(run, runtime).checks

    def test_should_check_the_forge_logins_in_the_preflight_wave(self):
        # Arrange
        equipment = CollectorEquipment(
            configuration=Configuration(forge_accounts={"build": "clauche-bot"}),
            forge=NoTokenForgeDouble(),
            forge_name="github",
            resolve_client=None,
        )

        # Act
        checks = self.run_built_in("wave", NO_PARAMETERS, equipment, create_test_runtime(self.paths))

        # Assert
        self.assertEqual(
            checks,
            [
                {
                    "name": "forge_logins",
                    "verdict": "fail",
                    "findings": ["gh printed no token for the login clauche-bot, bound to build"],
                }
            ],
        )

    def test_should_report_the_three_facts_of_a_draft_and_its_forge_logins_in_the_preflight_refinement(self):
        # Arrange
        equipment = CollectorEquipment(
            configuration=Configuration(), forge=NO_FORGE_PLUGIN, forge_name="none", resolve_client=None
        )
        runtime = create_test_runtime(self.paths, run_process=script_draft_processes())

        # Act
        checks = self.run_built_in("refinement", {"task": "B9"}, equipment, runtime)

        # Assert
        self.assertEqual(
            checks,
            [
                {
                    "name": "moved_citations",
                    "verdict": "fail",
                    "findings": [
                        "brigade/cart.py:3-4 moved since 22222222 to brigade/cart.py:5-6",
                        "brigade/shelf.py:9 changed since 22222222",
                    ],
                },
                {
                    "name": "tasks_outside_after",
                    "verdict": "fail",
                    "findings": ["@TASK.B4 (draft) touches brigade/till.py, outside the AFTER of @TASK.B9"],
                },
                {
                    "name": "overlapping_deliverables",
                    "verdict": "fail",
                    "findings": [
                        "@TASK.B3 (todo) cites brigade/till.py as @TASK.B9 does",
                        "@TASK.B4 (draft) cites brigade/till.py, @DECISION.ReceiptsAreKept as @TASK.B9 does",
                    ],
                },
                {"name": "forge_logins", "verdict": "pass", "findings": []},
            ],
        )
