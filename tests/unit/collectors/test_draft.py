import tempfile
import unittest
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collectors.draft import collect
from brigade.errors import BrigadeError
from brigade.system.parse_configuration import Configuration
from tests.unit.collectors.draft_processes import script_draft_processes
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses

EQUIPMENT = CollectorEquipment(configuration=Configuration(), forge=None, forge_name="none", resolve_client=None)


class DraftCollectorTest(unittest.TestCase):
    def test_should_collect_the_citations_of_the_draft_and_the_live_tasks_beside_it(self):
        # Arrange
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        runtime = create_test_runtime(create_test_paths(Path(directory.name)), run_process=script_draft_processes())
        environment = {
            "BRIGADE_PROJECT_PATH": "/srv/shop",
            "BRIGADE_SINCE": "1970-01-01",
            "BRIGADE_PARAMS": '{"task": "B9"}',
        }

        # Act
        document = collect(environment, runtime, EQUIPMENT)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "collector": "draft",
                "collected_at": "2026-10-19T09:00:00Z",
                "cache": False,
                "summary": {
                    "task": "B9",
                    "after": ["B3"],
                    "source_commit": "2222222222222222222222222222222222222222",
                    "files": ["brigade/cart.py", "brigade/till.py"],
                    "entities": ["@DECISION.ReceiptsAreKept"],
                    "citations": [
                        {
                            "citation": "brigade/cart.py:3-4",
                            "path": "brigade/cart.py",
                            "start": 3,
                            "end": 4,
                            "now": {"start": 5, "end": 6},
                        },
                        {
                            "citation": "brigade/till.py:7",
                            "path": "brigade/till.py",
                            "start": 7,
                            "end": 7,
                            "now": {"start": 7, "end": 7},
                        },
                        {
                            "citation": "brigade/shelf.py:9",
                            "path": "brigade/shelf.py",
                            "start": 9,
                            "end": 9,
                            "now": None,
                        },
                    ],
                },
                "items": [
                    {"task": "B3", "status": "todo", "files": ["brigade/till.py"], "entities": []},
                    {
                        "task": "B4",
                        "status": "draft",
                        "files": ["brigade/till.py"],
                        "entities": ["@DECISION.ReceiptsAreKept"],
                    },
                ],
            },
        )

    def test_should_refuse_a_draft_holding_no_source_naming_it(self):
        # Arrange
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        processes = ScriptedProcesses()
        processes.answer_json(
            ("awawa", "show", "@TASK.B9", "--json", "/srv/shop"),
            {"file": "./corpus/tasks.awawa", "line": 40, "fields": [{"name": "TITLE", "atoms": ['"the till"']}]},
        )
        processes.answer_json(
            ("awawa", "show", "./corpus/tasks.awawa", "--json", "/srv/shop"),
            {"entities": [{"type": "TASK", "name": "B9", "lines": [{"line": 41, "field_path": ["TITLE"]}]}]},
        )
        runtime = create_test_runtime(create_test_paths(Path(directory.name)), run_process=processes)
        environment = {
            "BRIGADE_PROJECT_PATH": "/srv/shop",
            "BRIGADE_SINCE": "1970-01-01",
            "BRIGADE_PARAMS": '{"task": "B9"}',
        }

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            collect(environment, runtime, EQUIPMENT)

        # Assert
        self.assertEqual(str(refusal.exception), "@TASK.B9 has no SOURCE: its citations have no commit to be read at")
