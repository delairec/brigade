import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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
    "\tFIELD MILESTONE @MILESTONE\n"
    "\tFIELD AFTER @TASK\n"
    "\t\tREPEATABLE\n"
)
TASK_SCHEMA_WITHOUT_MILESTONE = (
    "SCHEMA TASK\n"
    '\tDESC "a change delivered by one pull request"\n'
    "\tFIELD TITLE string\n"
    "\t\tREQUIRED\n"
    "\tFIELD STATUS draft|todo|implemented|archived\n"
    "\t\tREQUIRED\n"
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
        self.assertEqual(json.loads(completed.stdout)["missing"], [{"type": "MILESTONE"}])

    def test_should_name_the_milestone_type_missing_in_the_text(self):
        # Act
        completed = self.run_plan_context("R1")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("\nMissing schema MILESTONE\n", completed.stdout)


class BrigadePlanContextOnACorpusWhoseTaskSchemaDeclaresNoMilestoneTest(PlanContextTestCase):
    def setUp(self):
        super().setUp()
        self.register_project(f"{TASK_SCHEMA_WITHOUT_MILESTONE}\n{DECISION_SCHEMA}\n{MILESTONE_SCHEMA}")
        self.write_request("planning")

    def test_should_name_the_milestone_field_of_the_task_schema_missing_in_the_document(self):
        # Act
        completed = self.run_plan_context("R1", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["missing"], [{"type": "TASK", "field": "MILESTONE"}])

    def test_should_name_the_milestone_field_of_the_task_schema_missing_in_the_text(self):
        # Act
        completed = self.run_plan_context("R1")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("\nMissing field MILESTONE of schema TASK\n", completed.stdout)


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


PLAN = (
    "MILESTONE W1\n"
    '\tTITLE "Empty the cart in one click"\n'
    "\tSTATUS planned\n"
    "\n"
    "TASK S4\n"
    '\tTITLE "Empty the cart"\n'
    "\tSTATUS todo\n"
    '\tSPEC "one click leaves the cart empty"\n'
    "\tMILESTONE @MILESTONE.W1\n"
    "\tAFTER @TASK.S2\n"
)
PLAN_FAILING_LINT = (
    "MILESTONE W1\n"
    '\tTITLE "Empty the cart in one click"\n'
    "\tSTATUS planned\n"
    "\n"
    "TASK S4\n"
    '\tTITLE "Empty the cart"\n'
    "\tSTATUS doing\n"
    "\tMILESTONE @MILESTONE.W1\n"
)
PLAN_WITH_AN_UNDECLARED_TYPE_AND_FIELD = (
    "MILESTONE W1\n"
    '\tTITLE "Empty the cart in one click"\n'
    "\tSTATUS planned\n"
    "\n"
    "TASK S4\n"
    '\tTITLE "Empty the cart"\n'
    "\tSTATUS todo\n"
    "\tMILESTONE @MILESTONE.W1\n"
    '\tCOLOUR "red"\n'
    "\n"
    "EPIC E1\n"
    '\tTITLE "Checkout"\n'
)
PLAN_WITH_TWO_MILESTONES = (
    "MILESTONE W1\n"
    '\tTITLE "Empty the cart in one click"\n'
    "\tSTATUS planned\n"
    "\n"
    "MILESTONE W2\n"
    '\tTITLE "Pay in one click"\n'
    "\tSTATUS planned\n"
)
PLAN_WITH_A_TASK_OF_ANOTHER_MILESTONE = (
    "MILESTONE W1\n"
    '\tTITLE "Empty the cart in one click"\n'
    "\tSTATUS planned\n"
    "\n"
    "TASK S4\n"
    '\tTITLE "Empty the cart"\n'
    "\tSTATUS todo\n"
)
PLAN_WITH_A_DECISION = (
    "MILESTONE W1\n"
    '\tTITLE "Empty the cart in one click"\n'
    "\tSTATUS planned\n"
    "\n"
    "DECISION CartEmptiesInOneClick\n"
    '\tTITLE "the cart empties in one click"\n'
    "\tSTATUS active\n"
)
PLAN_REUSING_NAMES_OF_THE_CORPUS = (
    "MILESTONE W1\n"
    '\tTITLE "Empty the cart in one click"\n'
    "\tSTATUS planned\n"
    "\n"
    "TASK S2\n"
    '\tTITLE "Empty the cart"\n'
    "\tSTATUS todo\n"
    "\tMILESTONE @MILESTONE.W1\n"
)
OPEN_TASKS = 'TASK S2\n\tTITLE "Remove an item from the cart"\n\tSTATUS todo\n\tSPEC "a removed item leaves the cart"\n'
OPEN_DECISIONS = 'DECISION CartLivesInMemory\n\tTITLE "the cart lives in memory"\n\tSTATUS active\n'
RECORDED_TASKS = (
    f"{OPEN_TASKS}"
    "\n"
    "TASK S4\n"
    '\tTITLE "Empty the cart"\n'
    "\tSTATUS todo\n"
    '\tSPEC "one click leaves the cart empty"\n'
    "\tMILESTONE @MILESTONE.W1\n"
    "\tAFTER @TASK.S2\n"
)
RECORDED_MILESTONES = 'MILESTONE W1\n\tTITLE "Empty the cart in one click"\n\tSTATUS planned\n'
DONE_TASKS = (
    'TASK S1\n\tTITLE "Add an item to the cart"\n\tSTATUS implemented\n\tSPEC "an item added appears in the cart"\n'
)
TASK_SCHEMA_WITH_COLOUR = f"{TASK_SCHEMA}\tFIELD COLOUR string\n"
PLAN_WITH_A_COLOUR = (
    "MILESTONE W1\n"
    '\tTITLE "Empty the cart in one click"\n'
    "\tSTATUS planned\n"
    "\n"
    "TASK S4\n"
    '\tTITLE "Empty the cart"\n'
    "\tSTATUS todo\n"
    "\tMILESTONE @MILESTONE.W1\n"
    '\tCOLOUR "red"\n'
)
BRANCH = "integration/W1-empty-the-cart-in-one-click"
RUN = "20261013T174800Z-cb856f"
ANOTHER_RUN = "20261013T181500Z-4d9e21"


class PlanRecordTestCase(PlanContextTestCase):
    def setUp(self):
        super().setUp()
        self.register_project(f"{TASK_SCHEMA}\n{DECISION_SCHEMA}\n{MILESTONE_SCHEMA}", OPEN_TASKS, OPEN_DECISIONS)
        self.project.run_git("commit", "--quiet", "--message", "corpus")
        self.write_request("planning")
        self.plan_file = Path(self.root.name).resolve() / "plan.awawa"

    def run_plan_record(self, plan: str, *options: str, environment: dict | None = None):
        self.plan_file.write_text(plan)
        return self.machine.run_brigade(
            CLONE_ENTRY_POINT, "plan", "record", "R1", "--file", str(self.plan_file), *options, environment=environment
        )

    def describe_run_environment(self, run: str) -> dict:
        progress_file = self.machine.state_home / "brigade" / "runs" / run / "progress.md"
        return {**self.machine.describe_environment(), "BRIGADE_PROGRESS_FILE": str(progress_file)}

    def read_ledger_events(self) -> list[dict]:
        ledger_files = list((self.machine.state_home / "brigade" / "ledger").glob("*.jsonl"))
        return [json.loads(line) for line in ledger_files[0].read_text().splitlines()]


class BrigadePlanRecordOfAPlanTest(PlanRecordTestCase):
    def test_should_print_the_request_the_milestone_and_the_branch_as_a_versioned_document(self):
        # Act
        completed = self.run_plan_record(PLAN, "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {"schema_version": 1, "request": "R1", "milestone": "W1", "branch": BRANCH},
        )

    def test_should_print_the_request_the_milestone_and_the_branch_as_text(self):
        # Act
        completed = self.run_plan_record(PLAN)

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, f"recorded @REQUEST.R1 as @MILESTONE.W1 on {BRANCH}\n")

    def test_should_commit_the_tasks_beside_the_tasks_of_the_corpus_on_the_integration_branch(self):
        # Act
        self.run_plan_record(PLAN)

        # Assert
        self.assertEqual(self.project.run_git("show", f"{BRANCH}:corpus/tasks.awawa"), RECORDED_TASKS)

    def test_should_commit_the_milestone_in_a_file_of_its_type_on_the_integration_branch(self):
        # Act
        self.run_plan_record(PLAN)

        # Assert
        self.assertEqual(self.project.run_git("show", f"{BRANCH}:corpus/milestones.awawa"), RECORDED_MILESTONES)

    def test_should_cut_the_integration_branch_from_the_main_branch(self):
        # Arrange
        self.project.run_git("switch", "--quiet", "--create", "feat/s3")
        self.project.run_git("commit", "--quiet", "--allow-empty", "--message", "work ahead of main")

        # Act
        self.run_plan_record(PLAN)

        # Assert
        self.assertEqual(self.project.run_git("rev-parse", f"{BRANCH}~1"), self.project.run_git("rev-parse", "main"))

    def test_should_leave_the_checkout_of_the_project_on_its_branch_and_clean(self):
        # Act
        self.run_plan_record(PLAN)

        # Assert
        self.assertEqual(self.project.run_git("status", "--porcelain", "--branch"), "## main\n")

    def test_should_commit_the_tasks_in_the_file_of_the_corpus_already_holding_tasks(self):
        # Arrange
        self.project.run_git("mv", "corpus/tasks.awawa", "corpus/backlog.awawa")
        self.project.run_git("commit", "--quiet", "--message", "backlog")

        # Act
        self.run_plan_record(PLAN)

        # Assert
        self.assertEqual(self.project.run_git("show", f"{BRANCH}:corpus/backlog.awawa"), RECORDED_TASKS)

    def test_should_commit_the_tasks_in_the_first_file_of_the_corpus_folder_holding_tasks(self):
        # Arrange
        self.project.run_git("mv", "corpus/tasks.awawa", "corpus/backlog.awawa")
        self.project.write("corpus/done.awawa", DONE_TASKS)
        self.project.track("corpus")
        self.project.run_git("commit", "--quiet", "--message", "backlog and done")

        # Act
        self.run_plan_record(PLAN)

        # Assert
        self.assertEqual(self.project.run_git("show", f"{BRANCH}:corpus/backlog.awawa"), RECORDED_TASKS)
        self.assertEqual(self.project.run_git("show", f"{BRANCH}:corpus/done.awawa"), DONE_TASKS)

    def test_should_commit_the_tasks_under_the_corpus_folder_when_the_file_holding_tasks_lies_outside_it(self):
        # Arrange
        self.project.run_git("mv", "corpus/tasks.awawa", "tasks.awawa")
        self.project.run_git("commit", "--quiet", "--message", "tasks outside the corpus folder")

        # Act
        self.run_plan_record(PLAN)

        # Assert
        self.assertEqual(
            self.project.run_git("show", f"{BRANCH}:corpus/tasks.awawa"),
            "TASK S4\n"
            '\tTITLE "Empty the cart"\n'
            "\tSTATUS todo\n"
            '\tSPEC "one click leaves the cart empty"\n'
            "\tMILESTONE @MILESTONE.W1\n"
            "\tAFTER @TASK.S2\n",
        )

    def test_should_mark_the_request_planned_with_its_milestone_and_its_branch(self):
        # Act
        self.run_plan_record(PLAN)

        # Assert
        self.assertEqual(
            (self.machine.corpus / "requests.awawa").read_text(),
            "REQUEST R1\n"
            "\tPROJECT @PROJECT.shop\n"
            f'\tTEXT "{REQUEST_TEXT}"\n'
            "\tSTATUS planned\n"
            '\tMILESTONE "W1"\n'
            f'\tBRANCH "{BRANCH}"\n',
        )


class BrigadePlanRecordOnAProjectOfTheGithubForgeTest(PlanRecordTestCase):
    def test_should_push_the_integration_branch(self):
        # Arrange
        remote = Path(self.root.name).resolve() / "remote.git"
        self.project.run_git("init", "--quiet", "--bare", str(remote))
        projects = self.machine.corpus / "projects.awawa"
        projects.write_text(projects.read_text().replace('\tFORGE "none"\n', '\tFORGE "github"\n'))
        self.project.run_git("remote", "add", "origin", str(remote))

        # Act
        completed = self.run_plan_record(PLAN)

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(self.project.run_git("ls-remote", "--heads", "origin").split()[1], f"refs/heads/{BRANCH}")


class BrigadePlanRecordOfAPlanTheSchemaDoesNotDeclareTest(PlanRecordTestCase):
    def test_should_exit_1_naming_the_types_and_the_fields_the_schema_does_not_declare(self):
        # Act
        completed = self.run_plan_record(PLAN_WITH_AN_UNDECLARED_TYPE_AND_FIELD)

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(
            completed.stderr,
            "brigade plan record: the schema of the corpus of @PROJECT.shop does not declare"
            " the field COLOUR of TASK, the type EPIC\n",
        )


class BrigadePlanRecordOfAPlanReusingNamesOfTheCorpusTest(PlanRecordTestCase):
    def setUp(self):
        super().setUp()
        self.project.write("corpus/milestones.awawa", RECORDED_MILESTONES)
        self.project.track("corpus")
        self.project.run_git("commit", "--quiet", "--message", "milestone W1")

    def test_should_exit_1_naming_each_entity_and_where_it_sits_before_any_write(self):
        # Act
        completed = self.run_plan_record(PLAN_REUSING_NAMES_OF_THE_CORPUS)

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(
            completed.stderr,
            "brigade plan record: @MILESTONE.W1 already exists at corpus/milestones.awawa:1,"
            " @TASK.S2 already exists at corpus/tasks.awawa:1\n",
        )
        self.assertEqual(self.project.run_git("branch", "--list", "integration/*"), "")


class BrigadePlanRecordFromACheckoutBehindTheMainBranchTest(PlanRecordTestCase):
    def setUp(self):
        super().setUp()
        self.project.run_git("branch", "feat/s3")
        self.project.write("corpus/tasks.awawa", f'{OPEN_TASKS}\nTASK S4\n\tTITLE "Empty the cart"\n\tSTATUS todo\n')
        self.project.track("corpus")
        self.project.run_git("commit", "--quiet", "--message", "task S4")
        self.project.run_git("switch", "--quiet", "feat/s3")

    def test_should_exit_1_naming_the_entity_the_main_branch_holds_before_any_write(self):
        # Act
        completed = self.run_plan_record(PLAN)

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stderr, "brigade plan record: @TASK.S4 already exists at corpus/tasks.awawa:6\n")
        self.assertEqual(self.project.run_git("branch", "--list", "integration/*"), "")

    def test_should_spend_no_lint_round(self):
        # Act
        self.run_plan_record(PLAN)

        # Assert
        self.assertEqual(list((self.machine.state_home / "brigade" / "ledger").glob("*.jsonl")), [])


class BrigadePlanRecordFromACheckoutAheadOfTheMainBranchTest(PlanRecordTestCase):
    def test_should_exit_1_naming_the_field_the_schema_of_the_main_branch_does_not_declare(self):
        # Arrange
        self.project.run_git("switch", "--quiet", "--create", "feat/colour")
        self.project.write("corpus/_schema.awawa", f"{TASK_SCHEMA_WITH_COLOUR}\n{DECISION_SCHEMA}\n{MILESTONE_SCHEMA}")
        self.project.run_git("commit", "--quiet", "--all", "--message", "colour of a task")

        # Act
        completed = self.run_plan_record(PLAN_WITH_A_COLOUR)

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(
            completed.stderr,
            "brigade plan record: the schema of the corpus of @PROJECT.shop does not declare the field COLOUR of TASK\n",
        )


class BrigadePlanRecordOfAPlanThatIsNotOneMilestoneAndItsTasksTest(PlanRecordTestCase):
    def test_should_exit_1_naming_what_the_plan_holds_beyond_one_milestone_and_its_tasks(self):
        for plan, expected_stderr in [
            (PLAN_WITH_TWO_MILESTONES, "brigade plan record: the plan holds 2 MILESTONE entities, not one\n"),
            (
                PLAN_WITH_A_DECISION,
                (
                    "brigade plan record: the plan holds @DECISION.CartEmptiesInOneClick,"
                    " which is neither a MILESTONE nor a TASK\n"
                ),
            ),
            (
                PLAN_WITH_A_TASK_OF_ANOTHER_MILESTONE,
                "brigade plan record: the plan holds @TASK.S4, whose MILESTONE is not @MILESTONE.W1\n",
            ),
        ]:
            with self.subTest(expected_stderr=expected_stderr):
                # Act
                completed = self.run_plan_record(plan)

                # Assert
                self.assertEqual(completed.returncode, 1)
                self.assertEqual(completed.stderr, expected_stderr)


class BrigadePlanRecordOnAnExistingIntegrationBranchTest(PlanRecordTestCase):
    def test_should_exit_1_naming_the_branch_before_any_write(self):
        # Arrange
        self.project.run_git("branch", BRANCH)

        # Act
        completed = self.run_plan_record(PLAN)

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stderr, f"brigade plan record: the branch {BRANCH} already exists\n")


class BrigadePlanRecordOfARequestNotPlanningTest(PlanRecordTestCase):
    def test_should_exit_1_naming_the_request_and_its_status(self):
        # Arrange
        self.write_request("planned")

        # Act
        completed = self.run_plan_record(PLAN)

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stderr, "brigade plan record: @REQUEST.R1 is planned, not planning\n")


class BrigadePlanRecordOfAProjectWithoutACorpusTest(PlanContextTestCase):
    def test_should_exit_1_naming_the_project(self):
        # Arrange
        self.project.write("src/cart.py", CART)
        self.project.track("src")
        self.machine.run_brigade(CLONE_ENTRY_POINT, "project", "add", str(self.project.path))
        self.write_request("planning")
        plan_file = Path(self.root.name).resolve() / "plan.awawa"
        plan_file.write_text(PLAN)

        # Act
        completed = self.machine.run_brigade(CLONE_ENTRY_POINT, "plan", "record", "R1", "--file", str(plan_file))

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stderr, "brigade plan record: @PROJECT.shop declares no corpus\n")


class BrigadePlanRecordOfAPlanFailingLintTest(PlanRecordTestCase):
    def test_should_exit_1_printing_the_lint_output(self):
        # Act
        completed = self.run_plan_record(PLAN_FAILING_LINT)

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertRegex(
            completed.stderr,
            r"(?s)\Abrigade plan record: awawa lint --strict refused the change; the corpus is restored\n.*doing",
        )

    def test_should_leave_neither_branch_nor_worktree(self):
        # Act
        self.run_plan_record(PLAN_FAILING_LINT)

        # Assert
        self.assertEqual(self.project.run_git("branch", "--list", "integration/*"), "")
        self.assertEqual(len(self.project.run_git("worktree", "list").splitlines()), 1)

    def test_should_leave_the_request_planning(self):
        # Act
        self.run_plan_record(PLAN_FAILING_LINT)

        # Assert
        self.assertEqual(
            (self.machine.corpus / "requests.awawa").read_text(),
            f'REQUEST R1\n\tPROJECT @PROJECT.shop\n\tTEXT "{REQUEST_TEXT}"\n\tSTATUS planning\n',
        )

    def test_should_record_the_lint_failure_of_the_request_in_the_run(self):
        # Act
        self.run_plan_record(PLAN_FAILING_LINT, environment=self.describe_run_environment(RUN))

        # Assert
        self.assertEqual(
            self.read_ledger_events(),
            [{"schema_version": 1, "ts": mock.ANY, "event": "plan.lint_failed", "request": "R1", "run": RUN}],
        )

    def test_should_record_the_lint_failure_outside_a_run_without_a_run(self):
        # Act
        self.run_plan_record(PLAN_FAILING_LINT)

        # Assert
        self.assertEqual(
            self.read_ledger_events(),
            [{"schema_version": 1, "ts": mock.ANY, "event": "plan.lint_failed", "request": "R1", "run": None}],
        )


class BrigadePlanRecordAfterALintFailureInTheSameRunTest(PlanRecordTestCase):
    def setUp(self):
        super().setUp()
        self.run_plan_record(PLAN_FAILING_LINT, environment=self.describe_run_environment(RUN))

    def test_should_exit_1_naming_the_round_already_spent_before_any_write(self):
        # Act
        completed = self.run_plan_record(PLAN, environment=self.describe_run_environment(RUN))

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(
            completed.stderr,
            f"brigade plan record: @REQUEST.R1 spent its lint round in run {RUN}; the run ends blocked\n",
        )
        self.assertEqual(self.project.run_git("branch", "--list", "integration/*"), "")

    def test_should_record_the_corrected_plan_in_another_run(self):
        # Act
        completed = self.run_plan_record(PLAN, environment=self.describe_run_environment(ANOTHER_RUN))

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_should_record_the_corrected_plan_outside_a_run(self):
        # Act
        completed = self.run_plan_record(PLAN)

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
