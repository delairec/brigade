import json
import tempfile
import unittest
from pathlib import Path

from tests.awawa.provide_awawa import provide_awawa
from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine
from tests.cli.temporary_project import TemporaryProject

TASK_SCHEMA = (
    "SCHEMA TASK\n"
    '\tDESC "a change delivered by one pull request"\n'
    "\tFIELD TITLE string\n"
    "\t\tREQUIRED\n"
    "\tFIELD STATUS draft|todo|implemented|archived\n"
    "\t\tREQUIRED\n"
    "\tFIELD SPEC string\n"
    "\t\tREPEATABLE\n"
    "\t\tFIELD IMPL anchor\n"
    "\t\t\tREPEATABLE\n"
    "\tFIELD AFTER @TASK\n"
    "\t\tREPEATABLE\n"
)
DECISION_SCHEMA = (
    "SCHEMA DECISION\n"
    '\tDESC "a ruling of the project"\n'
    "\tFIELD TITLE string\n"
    "\t\tREQUIRED\n"
    "\tFIELD STATUS active|archived\n"
    "\t\tREQUIRED\n"
    "\tFIELD IMPL anchor\n"
    "\t\tREPEATABLE\n"
)
MILESTONE_SCHEMA = (
    "SCHEMA MILESTONE\n"
    '\tDESC "the tasks planned for one request"\n'
    "\tFIELD TITLE string\n"
    "\t\tREQUIRED\n"
    "\tFIELD STATUS planned|running|delivered\n"
    "\t\tREQUIRED\n"
)
TASKS = (
    "TASK FIX7\n"
    '\tTITLE "Round the total to the cent"\n'
    "\tSTATUS draft\n"
    '\tSPEC "the total is rounded to the cent"\n'
    "\n"
    "TASK S1\n"
    '\tTITLE "Add an item to the cart"\n'
    "\tSTATUS implemented\n"
    '\tSPEC "an item added appears in the cart"\n'
    '\t\tIMPL "src/cart.py::def add_item"\n'
    "\n"
    "TASK S2\n"
    '\tTITLE "Remove an item from the cart"\n'
    "\tSTATUS todo\n"
    '\tSPEC "a removed item leaves the cart"\n'
)
DECISIONS = (
    "DECISION CartLivesInADatabase\n"
    '\tTITLE "the cart lives in a database"\n'
    "\tSTATUS archived\n"
    "\n"
    "DECISION CartLivesInMemory\n"
    '\tTITLE "the cart lives in memory"\n'
    "\tSTATUS active\n"
    '\tIMPL "src/cart.py::CART = []"\n'
)
UNTITLED_TASK_SCHEMA = (
    "SCHEMA TASK\n"
    '\tDESC "a change delivered by one pull request"\n'
    "\tFIELD STATUS draft|todo|implemented|archived\n"
    "\t\tREQUIRED\n"
)
UNTITLED_DECISION_SCHEMA = (
    'SCHEMA DECISION\n\tDESC "a ruling of the project"\n\tFIELD STATUS active|archived\n\t\tREQUIRED\n'
)
UNTITLED_TASKS = "TASK S3\n\tSTATUS todo\n"
UNTITLED_DECISIONS = "DECISION CartLivesInMemory\n\tSTATUS active\n"
CART = "CART = []\n\n\ndef add_item(item):\n    CART.append(item)\n"
REQUEST_TEXT = "let the customer empty the cart in one click"


class PlanContextTestCase(unittest.TestCase):
    def setUp(self):
        provide_awawa(self)
        self.root = tempfile.TemporaryDirectory()
        root = Path(self.root.name).resolve()
        self.machine = TemporaryMachine(root)
        self.machine.run_init()
        self.project = TemporaryProject(root / "projects" / "shop", self.machine.describe_environment())

    def tearDown(self):
        self.root.cleanup()

    def write_corpus(self, schema: str, tasks: str, decisions: str) -> None:
        self.project.write("corpus/_schema.awawa", schema)
        self.project.write("corpus/tasks.awawa", tasks)
        self.project.write("corpus/decisions.awawa", decisions)

    def register_project(self, schema: str, tasks: str = TASKS, decisions: str = DECISIONS) -> None:
        self.write_corpus(schema, tasks, decisions)
        self.project.track("corpus")
        self.machine.run_brigade(CLONE_ENTRY_POINT, "project", "add", str(self.project.path))

    def write_request(self, status: str) -> None:
        (self.machine.corpus / "requests.awawa").write_text(
            f'REQUEST R1\n\tPROJECT @PROJECT.shop\n\tTEXT "{REQUEST_TEXT}"\n\tSTATUS {status}\n'
        )

    def run_plan_context(self, *arguments: str):
        return self.machine.run_brigade(CLONE_ENTRY_POINT, "plan", "context", *arguments)


class BrigadePlanContextOfAPlanningRequestTest(PlanContextTestCase):
    def setUp(self):
        super().setUp()
        self.register_project(f"{TASK_SCHEMA}\n{DECISION_SCHEMA}\n{MILESTONE_SCHEMA}")
        self.write_request("planning")

    def test_should_print_the_planning_package_as_a_versioned_document(self):
        # Act
        completed = self.run_plan_context("R1", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "request": {"name": "R1", "project": "shop", "text": REQUEST_TEXT},
                "corpus": str(self.project.path),
                "status": [
                    {"type": "DECISION", "total": 2, "counts": {"active": 1, "archived": 1}},
                    {"type": "MILESTONE", "total": 0, "counts": {}},
                    {"type": "SCHEMA", "total": 3, "counts": {}},
                    {"type": "TASK", "total": 3, "counts": {"draft": 1, "implemented": 1, "todo": 1}},
                ],
                "decisions": [{"name": "CartLivesInMemory", "title": "the cart lives in memory"}],
                "tasks": [
                    {"name": "FIX7", "status": "draft", "title": "Round the total to the cent"},
                    {"name": "S2", "status": "todo", "title": "Remove an item from the cart"},
                ],
                "schemas": {"TASK": TASK_SCHEMA, "MILESTONE": MILESTONE_SCHEMA},
                "missing": [],
                "next_task_number": 8,
                "anchors": {
                    "src/cart.py": [
                        {"entity": "@DECISION.CartLivesInMemory", "anchor": "src/cart.py::CART = []"},
                        {"entity": "@TASK.S1", "anchor": "src/cart.py::def add_item"},
                    ]
                },
            },
        )

    def test_should_print_the_planning_package_as_text(self):
        # Act
        completed = self.run_plan_context("R1")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout,
            "@REQUEST.R1 of @PROJECT.shop\n"
            f"{REQUEST_TEXT}\n"
            "\n"
            f"Corpus {self.project.path}\n"
            "DECISION   2  active 1, archived 1\n"
            "MILESTONE  0\n"
            "SCHEMA     3\n"
            "TASK       3  draft 1, implemented 1, todo 1\n"
            "\n"
            "Active decisions\n"
            "@DECISION.CartLivesInMemory  the cart lives in memory\n"
            "\n"
            "Draft and todo tasks\n"
            "@TASK.FIX7  draft  Round the total to the cent\n"
            "@TASK.S2  todo  Remove an item from the cart\n"
            "\n"
            "Next free task number 8\n"
            "\n"
            "Anchors by file\n"
            "src/cart.py\n"
            "  @DECISION.CartLivesInMemory  src/cart.py::CART = []\n"
            "  @TASK.S1  src/cart.py::def add_item\n"
            "\n"
            f"{TASK_SCHEMA}\n"
            f"{MILESTONE_SCHEMA}",
        )


class BrigadePlanContextOnACorpusWithoutAMilestoneTypeTest(PlanContextTestCase):
    def setUp(self):
        super().setUp()
        self.register_project(f"{TASK_SCHEMA}\n{DECISION_SCHEMA}")
        self.write_request("planning")

    def test_should_name_the_milestone_type_missing_in_the_document(self):
        # Act
        completed = self.run_plan_context("R1", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["missing"], ["MILESTONE"])

    def test_should_name_the_milestone_type_missing_in_the_text(self):
        # Act
        completed = self.run_plan_context("R1")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("\nMissing schema MILESTONE\n", completed.stdout)


class BrigadePlanContextOnACorpusListingNoTypeTest(PlanContextTestCase):
    def setUp(self):
        super().setUp()
        self.project.write("corpus/tasks.awawa")
        self.project.track("corpus")
        self.machine.run_brigade(CLONE_ENTRY_POINT, "project", "add", str(self.project.path))
        self.write_request("planning")

    def test_should_print_an_empty_inventory_and_name_both_schemas_missing(self):
        # Act
        completed = self.run_plan_context("R1")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout,
            "@REQUEST.R1 of @PROJECT.shop\n"
            f"{REQUEST_TEXT}\n"
            "\n"
            f"Corpus {self.project.path}\n"
            "\n"
            "Active decisions\n"
            "\n"
            "Draft and todo tasks\n"
            "\n"
            "Next free task number 1\n"
            "\n"
            "Anchors by file\n"
            "\n"
            "Missing schema TASK\n"
            "\n"
            "Missing schema MILESTONE\n",
        )


class BrigadePlanContextOfARequestNotPlanningTest(PlanContextTestCase):
    def test_should_exit_1_naming_the_request_and_its_status(self):
        # Arrange
        self.register_project(f"{TASK_SCHEMA}\n{DECISION_SCHEMA}\n{MILESTONE_SCHEMA}")
        self.write_request("planned")

        # Act
        completed = self.run_plan_context("R1")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stderr, "brigade plan context: @REQUEST.R1 is planned, not planning\n")


class BrigadePlanContextOfAnUnknownRequestTest(PlanContextTestCase):
    def test_should_exit_1_naming_the_request(self):
        # Arrange
        self.write_request("planning")

        # Act
        completed = self.run_plan_context("R9")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(
            completed.stderr, "brigade plan context: @REQUEST.R9 is not defined in the operational corpus\n"
        )


class BrigadePlanContextOfAProjectWithoutACorpusTest(PlanContextTestCase):
    def test_should_exit_1_naming_the_project(self):
        # Arrange
        self.project.write("src/cart.py", CART)
        self.project.track("src")
        self.machine.run_brigade(CLONE_ENTRY_POINT, "project", "add", str(self.project.path))
        self.write_request("planning")

        # Act
        completed = self.run_plan_context("R1")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stderr, "brigade plan context: @PROJECT.shop declares no corpus\n")


class BrigadePlanContextOnACorpusWhoseEntityHoldsNoTitleTest(PlanContextTestCase):
    def setUp(self):
        super().setUp()
        self.register_project(f"{TASK_SCHEMA}\n{DECISION_SCHEMA}\n{MILESTONE_SCHEMA}")
        self.write_request("planning")

    def test_should_exit_1_naming_the_entity_and_the_field(self):
        for schema, tasks, decisions, expected_stderr in [
            (
                f"{UNTITLED_TASK_SCHEMA}\n{DECISION_SCHEMA}\n{MILESTONE_SCHEMA}",
                UNTITLED_TASKS,
                DECISIONS,
                "brigade plan context: @TASK.S3 holds no TITLE\n",
            ),
            (
                f"{TASK_SCHEMA}\n{UNTITLED_DECISION_SCHEMA}\n{MILESTONE_SCHEMA}",
                TASKS,
                UNTITLED_DECISIONS,
                "brigade plan context: @DECISION.CartLivesInMemory holds no TITLE\n",
            ),
        ]:
            with self.subTest(expected_stderr=expected_stderr):
                # Arrange
                self.write_corpus(schema, tasks, decisions)

                # Act
                completed = self.run_plan_context("R1")

                # Assert
                self.assertEqual(completed.returncode, 1)
                self.assertEqual(completed.stderr, expected_stderr)
