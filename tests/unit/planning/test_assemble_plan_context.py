import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.planning.assemble_plan_context import assemble_plan_context

ROOT = Path("/srv/shop")
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
        self.documents = {
            (ROOT, ("status",)): STATUS,
            (ROOT, ("show", "@DECISION.D1")): DECISION_D1,
            (ROOT, ("show", "@DECISION.D2")): DECISION_D2,
            (ROOT, ("show", "@TASK.B7")): TASK_B7,
        }
        self.schemas = {(ROOT, "MILESTONE"): None}

    def read_awawa_document(self, root: Path, arguments: tuple[str, ...]) -> dict:
        return self.documents[(root, arguments)]

    def read_schema(self, root: Path, entity_type: str) -> str | None:
        return self.schemas[(root, entity_type)]

    def assemble(self) -> dict:
        return assemble_plan_context(self.read_awawa_document, self.read_schema, ROOT)

    def script_task_schema(self, schema: dict) -> None:
        self.schemas[(ROOT, "TASK")] = "SCHEMA TASK\n"
        self.documents[(ROOT, ("show", "TASK"))] = schema

    def test_should_assemble_what_a_planning_run_needs_to_know_of_the_corpus(self):
        # Arrange
        self.documents[(ROOT, ("show", "@TASK.B2"))] = TASK_B2
        self.script_task_schema(TASK_SCHEMA)

        # Act
        context = self.assemble()

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
        self.documents[(ROOT, ("status",))] = {
            "types": [{"type": "TASK", "total": 1, "counts": {"draft": 0, "todo": 1}}],
            "entities": [],
        }
        self.script_task_schema(TASK_SCHEMA)

        # Act
        context = self.assemble()

        # Assert
        self.assertEqual(context["status"], [{"type": "TASK", "total": 1, "counts": {"todo": 1}}])

    def test_should_report_nothing_missing_of_a_task_schema_declaring_its_milestone(self):
        # Arrange
        self.documents[(ROOT, ("show", "@TASK.B2"))] = TASK_B2
        self.script_task_schema({"fields": [{"name": "FIELD", "atoms": ["MILESTONE", "reference"]}]})

        # Act
        context = self.assemble()

        # Assert
        self.assertEqual(context["missing"], [{"type": "MILESTONE"}])

    def test_should_report_a_missing_task_schema_alone(self):
        # Arrange
        self.documents[(ROOT, ("show", "@TASK.B2"))] = TASK_B2
        self.schemas[(ROOT, "TASK")] = None

        # Act
        context = self.assemble()

        # Assert
        self.assertEqual(context["missing"], [{"type": "TASK"}, {"type": "MILESTONE"}])

    def test_should_refuse_an_open_task_without_a_title(self):
        # Arrange
        self.documents[(ROOT, ("show", "@TASK.B2"))] = {"type": "TASK", "name": "B2", "status": "todo", "fields": []}
        self.script_task_schema(TASK_SCHEMA)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            self.assemble()

        # Assert
        self.assertEqual(str(refusal.exception), "@TASK.B2 holds no TITLE")

    def test_should_count_the_schemas_among_the_types_of_the_corpus(self):
        # Arrange
        self.documents[(ROOT, ("status",))] = {"types": [{"type": "SCHEMA", "total": 2, "counts": {}}], "entities": []}
        self.script_task_schema(TASK_SCHEMA)

        # Act
        context = self.assemble()

        # Assert
        self.assertEqual(context["status"], [{"type": "SCHEMA", "total": 2, "counts": {}}])

    def test_should_carry_the_text_of_both_planned_schemas(self):
        # Arrange
        self.documents[(ROOT, ("show", "@TASK.B2"))] = TASK_B2
        self.script_task_schema(TASK_SCHEMA)
        self.schemas[(ROOT, "MILESTONE")] = "SCHEMA MILESTONE\n"

        # Act
        context = self.assemble()

        # Assert
        self.assertEqual(context["schemas"], {"TASK": "SCHEMA TASK\n", "MILESTONE": "SCHEMA MILESTONE\n"})

    def test_should_report_the_milestone_field_of_the_task_schema_missing_alone(self):
        # Arrange
        self.documents[(ROOT, ("show", "@TASK.B2"))] = TASK_B2
        self.script_task_schema(TASK_SCHEMA)
        self.schemas[(ROOT, "MILESTONE")] = "SCHEMA MILESTONE\n"

        # Act
        context = self.assemble()

        # Assert
        self.assertEqual(context["missing"], [{"type": "TASK", "field": "MILESTONE"}])

    def test_should_index_the_anchors_of_one_file_in_the_order_of_the_corpus(self):
        # Arrange
        self.documents[(ROOT, ("show", "@DECISION.D1"))] = {
            "type": "DECISION",
            "name": "D1",
            "status": "active",
            "fields": [
                {"name": "TITLE", "atoms": ['"one store"'], "fields": []},
                {"name": "IMPL", "atoms": ['"brigade/parse.py::read"'], "fields": []},
            ],
        }
        self.documents[(ROOT, ("show", "@TASK.B2"))] = TASK_B2
        self.script_task_schema(TASK_SCHEMA)

        # Act
        context = self.assemble()

        # Assert
        self.assertEqual(
            context["anchors"],
            {
                "brigade/parse.py": [
                    {"entity": "@DECISION.D1", "anchor": "brigade/parse.py::read"},
                    {"entity": "@TASK.B2", "anchor": "brigade/parse.py::parse"},
                ]
            },
        )

    def test_should_refuse_an_active_decision_without_a_title(self):
        # Arrange
        self.documents[(ROOT, ("show", "@DECISION.D1"))] = {
            "type": "DECISION",
            "name": "D1",
            "status": "active",
            "fields": [],
        }
        self.documents[(ROOT, ("show", "@TASK.B2"))] = TASK_B2
        self.script_task_schema(TASK_SCHEMA)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            self.assemble()

        # Assert
        self.assertEqual(str(refusal.exception), "@DECISION.D1 holds no TITLE")

    def test_should_keep_in_a_title_the_backslash_awawa_keeps(self):
        # Arrange
        self.documents[(ROOT, ("show", "@TASK.B2"))] = {
            **TASK_B2,
            "fields": [{"name": "TITLE", "atoms": [r'"the \.awawa parser"'], "fields": []}],
        }
        self.script_task_schema(TASK_SCHEMA)

        # Act
        context = self.assemble()

        # Assert
        self.assertEqual(context["tasks"], [{"name": "B2", "status": "draft", "title": r"the \.awawa parser"}])
