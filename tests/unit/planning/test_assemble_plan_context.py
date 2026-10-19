import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.planning.assemble_plan_context import assemble_plan_context
from tests.unit.scripted_processes import ScriptedProcesses

STATUS = {
    "types": [
        {"type": "DECISION", "total": 2, "counts": {"active": 1, "archived": 1}},
        {"type": "TASK", "total": 3, "counts": {"draft": 1, "todo": 1, "implemented": 1}},
    ],
    "entities": [
        {"type": "SCHEMA", "name": "TASK", "target": "TASK"},
        {"type": "DECISION", "name": "D1", "target": "@DECISION.D1"},
        {"type": "DECISION", "name": "D2", "target": "@DECISION.D2"},
        {"type": "TASK", "name": "B2", "target": "@TASK.B2"},
        {"type": "TASK", "name": "B7", "target": "@TASK.B7"},
    ],
}
DECISION_D1 = {
    "type": "DECISION",
    "name": "D1",
    "status": "active",
    "fields": [{"name": "TITLE", "atoms": ['"one store"'], "fields": []}],
}
DECISION_D2 = {
    "type": "DECISION",
    "name": "D2",
    "status": "archived",
    "fields": [{"name": "TITLE", "atoms": ['"two stores"'], "fields": []}],
}
TASK_B2 = {
    "type": "TASK",
    "name": "B2",
    "status": "draft",
    "fields": [
        {"name": "TITLE", "atoms": ['"the "', '"parser"'], "fields": []},
        {
            "name": "SPEC",
            "atoms": ['"parses"'],
            "fields": [{"name": "IMPL", "atoms": ['"brigade/parse.py::parse"'], "fields": []}],
        },
    ],
}
TASK_B7 = {
    "type": "TASK",
    "name": "B7",
    "status": "implemented",
    "fields": [{"name": "TITLE", "atoms": ['"the printer"'], "fields": []}],
}
TASK_SCHEMA = {"fields": [{"name": "FIELD", "atoms": ["TITLE", "string"]}, {"name": "DESC", "atoms": ['"a task"']}]}


class AssemblePlanContextTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.processes = ScriptedProcesses()
        root = str(self.root)
        self.processes.answer_json(("awawa", "status", "--json", root), STATUS)
        self.processes.answer_json(("awawa", "show", "@DECISION.D1", "--json", root), DECISION_D1)
        self.processes.answer_json(("awawa", "show", "@DECISION.D2", "--json", root), DECISION_D2)
        self.processes.answer_json(("awawa", "show", "@TASK.B7", "--json", root), TASK_B7)
        self.processes.answer(("awawa", "show", "MILESTONE", root), exit_code=1)

    def script_task_schema(self, schema: dict) -> None:
        root = str(self.root)
        self.processes.answer(("awawa", "show", "TASK", root), stdout="SCHEMA TASK\n")
        self.processes.answer_json(("awawa", "show", "TASK", "--json", root), schema)

    def test_should_assemble_what_a_planning_run_needs_to_know_of_the_corpus(self):
        # Arrange
        self.processes.answer_json(("awawa", "show", "@TASK.B2", "--json", str(self.root)), TASK_B2)
        self.script_task_schema(TASK_SCHEMA)

        # Act
        context = assemble_plan_context(self.processes, self.root)

        # Assert
        self.assertEqual(
            context,
            {
                "status": [
                    {"type": "DECISION", "total": 2, "counts": {"active": 1, "archived": 1}},
                    {"type": "TASK", "total": 3, "counts": {"draft": 1, "todo": 1, "implemented": 1}},
                ],
                "decisions": [{"name": "D1", "title": "one store"}],
                "tasks": [{"name": "B2", "status": "draft", "title": "the parser"}],
                "schemas": {"TASK": "SCHEMA TASK\n"},
                "missing": [{"type": "MILESTONE"}, {"type": "TASK", "field": "MILESTONE"}],
                "next_task_number": 8,
                "anchors": {"brigade/parse.py": [{"entity": "@TASK.B2", "anchor": "brigade/parse.py::parse"}]},
            },
        )

    def test_should_leave_out_of_the_status_the_statuses_no_entity_holds(self):
        # Arrange
        self.processes.answer_json(
            ("awawa", "status", "--json", str(self.root)),
            {"types": [{"type": "TASK", "total": 1, "counts": {"draft": 0, "todo": 1}}], "entities": []},
        )
        self.script_task_schema(TASK_SCHEMA)

        # Act
        context = assemble_plan_context(self.processes, self.root)

        # Assert
        self.assertEqual(context["status"], [{"type": "TASK", "total": 1, "counts": {"todo": 1}}])

    def test_should_report_nothing_missing_of_a_task_schema_declaring_its_milestone(self):
        # Arrange
        self.processes.answer_json(("awawa", "show", "@TASK.B2", "--json", str(self.root)), TASK_B2)
        self.script_task_schema({"fields": [{"name": "FIELD", "atoms": ["MILESTONE", "reference"]}]})

        # Act
        context = assemble_plan_context(self.processes, self.root)

        # Assert
        self.assertEqual(context["missing"], [{"type": "MILESTONE"}])

    def test_should_report_a_missing_task_schema_alone(self):
        # Arrange
        self.processes.answer_json(("awawa", "show", "@TASK.B2", "--json", str(self.root)), TASK_B2)
        self.processes.answer(("awawa", "show", "TASK", str(self.root)), exit_code=1)

        # Act
        context = assemble_plan_context(self.processes, self.root)

        # Assert
        self.assertEqual(context["missing"], [{"type": "TASK"}, {"type": "MILESTONE"}])

    def test_should_refuse_an_open_task_without_a_title(self):
        # Arrange
        self.processes.answer_json(
            ("awawa", "show", "@TASK.B2", "--json", str(self.root)),
            {"type": "TASK", "name": "B2", "status": "todo", "fields": []},
        )
        self.script_task_schema(TASK_SCHEMA)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            assemble_plan_context(self.processes, self.root)

        # Assert
        self.assertEqual(str(refusal.exception), "@TASK.B2 holds no TITLE")
