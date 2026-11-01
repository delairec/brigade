import json
import os
import tempfile
import unittest
from pathlib import Path

from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine
from tests.cli.temporary_project import TemporaryProject
from tests.cli.test_collect import install_executable

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
REQUEST_TEXT = "let the customer empty the cart in one click"


class PlanContextTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        root = Path(self.root.name).resolve()
        self.machine = TemporaryMachine(root)
        self.machine.install_awawa(self)
        self.machine.run_init()
        self.project = TemporaryProject(root / "projects" / "shop", self.machine.describe_environment())

    def tearDown(self):
        self.root.cleanup()

    def write_corpus(self, schema: str, tasks: str, decisions: str) -> None:
        self.project.write("corpus/_schema.awawa", schema)
        self.project.write("corpus/tasks.awawa", tasks)
        self.project.write("corpus/decisions.awawa", decisions)

    def commit_corpus(self) -> None:
        self.project.track("corpus")
        self.project.run_git("commit", "--quiet", "--message", "corpus")

    def locate_main_tree(self) -> Path:
        return self.machine.cache_home / "brigade" / "refs" / "shop" / self.project.run_git("rev-parse", "main").strip()

    def register_project(self, schema: str, tasks: str = TASKS, decisions: str = DECISIONS) -> None:
        self.write_corpus(schema, tasks, decisions)
        self.commit_corpus()
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
                "corpus": str(self.locate_main_tree()),
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
            f"Corpus {self.locate_main_tree()}\n"
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
OPEN_TASKS = 'TASK S2\n\tTITLE "Remove an item from the cart"\n\tSTATUS todo\n\tSPEC "a removed item leaves the cart"\n'
OPEN_DECISIONS = 'DECISION CartLivesInMemory\n\tTITLE "the cart lives in memory"\n\tSTATUS active\n'
BRANCH = "plan/R1"
FAKE_GH = (
    "#!/bin/sh\n"
    'printf \'%s %s\\n\' "${{GH_TOKEN:-unbound}}" "$*" >> "{calls}"\n'
    'case "$1 $2" in\n'
    '  "auth token") echo "token-of-$6" ;;\n'
    '  "pr create") cat > /dev/null; echo https://github.com/acme/shop/pull/42 ;;\n'
    '  "pr list") cat "{listed}" ;;\n'
    '  "pr view") cat "{viewed}" ;;\n'
    '  "api repos/"*) echo 0 ;;\n'
    "esac\n"
)
FORGE_ACCOUNTS = '[forge_accounts]\ncli = "octo-cli"\nreview = "octo-review"\n'


class PlanRecordTestCase(PlanContextTestCase):
    def setUp(self):
        super().setUp()
        self.register_project(f"{TASK_SCHEMA}\n{DECISION_SCHEMA}\n{MILESTONE_SCHEMA}", OPEN_TASKS, OPEN_DECISIONS)
        self.write_request("planning")
        self.plan_file = Path(self.root.name).resolve() / "plan.awawa"

    def run_plan_record(self, plan: str, *options: str, environment: dict | None = None):
        self.plan_file.write_text(plan)
        return self.machine.run_brigade(
            CLONE_ENTRY_POINT, "plan", "record", "R1", "--file", str(self.plan_file), *options, environment=environment
        )


class BrigadePlanRecordOfAPlanTest(PlanRecordTestCase):
    def test_should_print_the_request_the_milestone_and_the_branch_as_a_versioned_document(self):
        # Act
        completed = self.run_plan_record(PLAN, "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {"schema_version": 1, "request": "R1", "milestone": "W1", "branch": BRANCH, "pr": None},
        )

    def test_should_print_the_request_the_milestone_and_the_branch_as_text(self):
        # Act
        completed = self.run_plan_record(PLAN)

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, f"recorded @REQUEST.R1 as @MILESTONE.W1 on {BRANCH}\n")


class PlanRecordOnTheGithubForgeTestCase(PlanRecordTestCase):
    def setUp(self):
        super().setUp()
        root = Path(self.root.name).resolve()
        remote = root / "remote.git"
        self.project.run_git("init", "--quiet", "--bare", str(remote))
        projects = self.machine.corpus / "projects.awawa"
        projects.write_text(projects.read_text().replace('\tFORGE "none"\n', '\tFORGE "github"\n'))
        self.project.run_git("remote", "add", "origin", str(remote))
        self.project.run_git("push", "--quiet", "origin", "main")
        self.gh_calls = root / "gh-calls"
        self.listed = root / "listed-pull-requests.json"
        self.viewed = root / "viewed-pull-request.json"
        self.answer_review_decision(None)
        install_executable(
            root / "tools" / "gh", FAKE_GH.format(calls=self.gh_calls, listed=self.listed, viewed=self.viewed)
        )
        self.machine.write_configuration(FORGE_ACCOUNTS)

    def answer_review_decision(self, review_decision: str | None) -> None:
        pull_request = {
            "number": 42,
            "state": "OPEN",
            "headRefOid": "0123456789abcdef",
            "baseRefName": "main",
            "reviewDecision": review_decision,
            "updatedAt": "2026-10-18T11:00:00Z",
            "statusCheckRollup": [],
            "commits": [],
        }
        self.listed.write_text(json.dumps([pull_request]))
        self.viewed.write_text(json.dumps(pull_request))

    def run_plan_record_on_github(self, *options: str):
        tools = Path(self.root.name).resolve() / "tools"
        environment = {**self.machine.describe_environment(), "PATH": f"{tools}{os.pathsep}{self.machine.search_path}"}
        return self.run_plan_record(PLAN, *options, environment=environment)


class BrigadePlanRecordOnAProjectOfTheGithubForgeTest(PlanRecordOnTheGithubForgeTestCase):
    def test_should_print_the_pull_request(self):
        # Act
        completed = self.run_plan_record_on_github("--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["pr"], 42)


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
