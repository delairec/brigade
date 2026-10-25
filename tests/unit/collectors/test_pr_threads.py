import tempfile
import unittest
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collectors.pr_threads import collect
from brigade.errors import BrigadeError
from brigade.system.parse_configuration import Configuration
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.forge_double import ForgeDouble
from tests.unit.scripted_processes import ScriptedProcesses

OPEN_PULL_REQUESTS = [{"number": 4, "head": "task/f0-parser/B12"}, {"number": 3, "head": "docs/readme"}]
THREADS_BY_PULL_REQUEST = {
    4: [
        {"id": "PRRT_kw4a", "file": "src/cart.py", "line": 12, "author": "delairec", "body": "Name the total"},
        {"id": "PRRT_kw4b", "file": "src/cart.py", "line": 12, "author": "delairec", "body": "Test the empty cart"},
    ],
    3: [],
}
NO_OPEN_PULL_REQUEST = []


def create_environment() -> dict:
    return {"BRIGADE_PROJECT_PATH": "/srv/oak", "BRIGADE_SINCE": "2026-10-01", "BRIGADE_PARAMS": "{}"}


def create_forge(pull_requests: list[dict]) -> ForgeDouble:
    return ForgeDouble(
        {
            "list_pull_requests": lambda request: {"schema_version": 1, "pull_requests": pull_requests},
            "list_review_threads": lambda request: {
                "schema_version": 1,
                "threads": THREADS_BY_PULL_REQUEST[request["number"]],
            },
        }
    )


class PrThreadsCollectorTest(unittest.TestCase):
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

    def test_should_list_the_unresolved_review_threads_of_the_open_pull_requests_counted_per_pull_request(self):
        # Arrange
        self.register_project("github")

        # Act
        document = collect(create_environment(), self.runtime, self.create_equipment(create_forge(OPEN_PULL_REQUESTS)))

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "collector": "pr-threads",
                "collected_at": "2026-10-19T09:00:00Z",
                "cache": False,
                "summary": {"4": 2, "3": 0},
                "items": [
                    {
                        "thread": "PRRT_kw4a",
                        "pull_request": 4,
                        "path": "src/cart.py",
                        "line": 12,
                        "author": "delairec",
                        "comment": "Name the total",
                    },
                    {
                        "thread": "PRRT_kw4b",
                        "pull_request": 4,
                        "path": "src/cart.py",
                        "line": 12,
                        "author": "delairec",
                        "comment": "Test the empty cart",
                    },
                ],
            },
        )

    def test_should_ask_the_forge_for_the_open_pull_requests_with_no_account_bound_by_default(self):
        # Arrange
        self.register_project("github")
        forge = create_forge(NO_OPEN_PULL_REQUEST)

        # Act
        collect(create_environment(), self.runtime, self.create_equipment(forge))

        # Assert
        self.assertEqual(
            forge.list_requests("list_pull_requests"),
            [{"schema_version": 1, "repository": "/srv/oak", "state": "open", "environment": {}}],
        )

    def test_should_ask_the_forge_for_the_review_threads_of_each_open_pull_request(self):
        # Arrange
        self.register_project("github")
        forge = create_forge(OPEN_PULL_REQUESTS)

        # Act
        collect(create_environment(), self.runtime, self.create_equipment(forge))

        # Assert
        self.assertEqual(
            forge.list_requests("list_review_threads"),
            [
                {"schema_version": 1, "repository": "/srv/oak", "number": 4, "environment": {}},
                {"schema_version": 1, "repository": "/srv/oak", "number": 3, "environment": {}},
            ],
        )

    def test_should_refuse_a_project_without_a_forge(self):
        # Arrange
        self.register_project("none")

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            collect(create_environment(), self.runtime, self.create_equipment(create_forge(OPEN_PULL_REQUESTS)))

        # Assert
        self.assertEqual(str(refusal.exception), "pr-threads is absent: FORGE none")

    def test_should_ask_nothing_of_the_forge_for_a_project_without_a_forge(self):
        # Arrange
        self.register_project("none")
        forge = create_forge(OPEN_PULL_REQUESTS)

        # Act
        with self.assertRaises(BrigadeError):
            collect(create_environment(), self.runtime, self.create_equipment(forge))

        # Assert
        self.assertEqual(forge.list_operations(), [])
