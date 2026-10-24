import tempfile
import unittest
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collectors.pr_list import collect
from brigade.errors import BrigadeError
from brigade.system.parse_configuration import Configuration
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.forge_double import ForgeDouble
from tests.unit.scripted_processes import ScriptedProcesses

PULL_REQUESTS = [
    {"number": 4, "head": "task/f0-parser/B12", "state": "open"},
    {"number": 3, "head": "docs/readme", "state": "merged"},
]


def create_environment(parameters: str) -> dict:
    return {"BRIGADE_PROJECT_PATH": "/srv/oak", "BRIGADE_SINCE": "2026-10-01", "BRIGADE_PARAMS": parameters}


class PrListCollectorTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.processes = ScriptedProcesses()
        write_operational_corpus(Path(directory.name))
        self.runtime = create_test_runtime(create_test_paths(Path(directory.name)), run_process=self.processes)

    def register_project(self, forge: str) -> None:
        self.processes.answer_entities(
            self.runtime.paths.config_root, "PROJECT", {"oak": (("PATH", "/srv/oak"), ("FORGE", forge))}
        )

    def create_equipment(self, forge: ForgeDouble) -> CollectorEquipment:
        return CollectorEquipment(configuration=Configuration(), forge=forge, forge_name="github")

    def test_should_list_the_pull_requests_with_the_task_their_branch_delivers(self):
        # Arrange
        self.register_project("github")
        forge = ForgeDouble(
            {"list_pull_requests": lambda request: {"schema_version": 1, "pull_requests": PULL_REQUESTS}}
        )

        # Act
        document = collect(create_environment("{}"), self.runtime, self.create_equipment(forge))

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "collector": "pr-list",
                "collected_at": "2026-10-19T09:00:00Z",
                "cache": False,
                "summary": {"open": 1, "merged": 1, "closed": 0},
                "items": [
                    {"number": 4, "head": "task/f0-parser/B12", "state": "open", "task": "B12"},
                    {"number": 3, "head": "docs/readme", "state": "merged", "task": None},
                ],
            },
        )

    def test_should_ask_the_forge_for_the_open_pull_requests_with_no_account_bound_by_default(self):
        # Arrange
        self.register_project("github")
        forge = ForgeDouble({"list_pull_requests": lambda request: {"schema_version": 1, "pull_requests": []}})

        # Act
        collect(create_environment("{}"), self.runtime, self.create_equipment(forge))

        # Assert
        self.assertEqual(
            forge.list_requests("list_pull_requests"),
            [{"schema_version": 1, "repository": "/srv/oak", "state": "open", "environment": {}}],
        )

    def test_should_ask_the_forge_for_the_state_it_is_given(self):
        # Arrange
        self.register_project("github")
        forge = ForgeDouble({"list_pull_requests": lambda request: {"schema_version": 1, "pull_requests": []}})

        # Act
        collect(create_environment('{"state": "all"}'), self.runtime, self.create_equipment(forge))

        # Assert
        self.assertEqual(forge.list_requests("list_pull_requests")[0]["state"], "all")

    def test_should_refuse_a_state_the_forge_does_not_know(self):
        # Arrange
        self.register_project("github")
        forge = ForgeDouble({"list_pull_requests": lambda request: {"schema_version": 1, "pull_requests": []}})

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            collect(create_environment('{"state": "draft"}'), self.runtime, self.create_equipment(forge))

        # Assert
        self.assertEqual(
            str(refusal.exception), "the parameter state of pr-list takes open, merged, closed or all, not draft"
        )

    def test_should_refuse_a_project_without_a_forge(self):
        # Arrange
        self.register_project("none")
        forge = ForgeDouble({"list_pull_requests": lambda request: {"schema_version": 1, "pull_requests": []}})

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            collect(create_environment("{}"), self.runtime, self.create_equipment(forge))

        # Assert
        self.assertEqual(str(refusal.exception), "pr-list is absent: FORGE none")

    def test_should_ask_nothing_of_the_forge_for_a_project_without_a_forge(self):
        # Arrange
        self.register_project("none")
        forge = ForgeDouble({"list_pull_requests": lambda request: {"schema_version": 1, "pull_requests": []}})

        # Act
        with self.assertRaises(BrigadeError):
            collect(create_environment("{}"), self.runtime, self.create_equipment(forge))

        # Assert
        self.assertEqual(forge.list_requests("list_pull_requests"), [])
