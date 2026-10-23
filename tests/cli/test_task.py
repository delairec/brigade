import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import ANY

from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine
from tests.cli.temporary_project import PINNED_COMMIT_DATES, TemporaryProject

PROJECT_SCHEMA = (
    "SCHEMA TASK\n"
    '\tDESC "a change delivered by one pull request"\n'
    "\tFIELD TITLE string\n\t\tREQUIRED\n"
    "\tFIELD STATUS todo|implemented\n\t\tREQUIRED\n"
    "\tFIELD MILESTONE @MILESTONE\n"
    "\tFIELD SPEC string\n\t\tREPEATABLE\n\t\tFIELD IMPL anchor\n\t\t\tREPEATABLE\n"
    "\n"
    "SCHEMA MILESTONE\n"
    '\tDESC "the tasks planned for one request"\n'
    "\tFIELD TITLE string\n\t\tREQUIRED\n"
    "\tFIELD STATUS planned|running\n\t\tREQUIRED\n"
)
MAIN_TASKS = 'TASK S2\n\tTITLE "Remove an item from the cart"\n\tSTATUS implemented\n'
WAVE_TASKS = (
    'TASK S2\n\tTITLE "Remove an item from the cart"\n\tSTATUS implemented\n\n'
    'TASK S3\n\tTITLE "Empty the cart in one click"\n\tSTATUS todo\n\tMILESTONE @MILESTONE.M1\n'
    '\tSPEC "the button of src/cart/button.py, once pressed, empties the cart"\n'
    '\tSPEC "the emptying charges nothing"\n\t\tIMPL "src/billing/charge.py::def charge"\n\n'
    'TASK S6\n\tTITLE "Count the emptied carts"\n\tSTATUS todo\n\tMILESTONE @MILESTONE.M1\n'
)
TASK_ADDED_ON_THE_WAVE = 'TASK S9\n\tTITLE "Name the emptied carts"\n\tSTATUS todo\n\tMILESTONE @MILESTONE.M1\n'
WAVE_MILESTONES = 'MILESTONE M1\n\tTITLE "Empty cart"\n\tSTATUS running\n'
REPEATED_MILESTONE = 'MILESTONE M1\n\tTITLE "Empty cart again"\n\tSTATUS running\n'
WAVE_BRANCH = "integration/M1-empty-cart"
TASK_BRANCH = "task/M1-empty-cart/S3"
WAVE_STARTED = (
    '{"schema_version": 2, "ts": "2026-10-13T09:00:00Z", "event": "wave.started", "wave": "shop_w1",'
    f' "project": "shop", "branch": "{WAVE_BRANCH}", "tasks": ["S3", "S6"]}}\n'
)
ACCEPTANCE_COMMAND = "python3 -m unittest"
HEAVY_COMMAND = "python3 -m unittest discover tests/e2e"
SETUP_LOG = "$ touch setup-ran\n"
AGENTS_TEXT = "# AGENTS.md — shop\n\nRun the tests with python3 -m unittest.\n"
INSTRUCTIONS_SCHEMA = (
    "SCHEMA TRIGGER\n"
    '\tDESC "a condition a session establishes"\n'
    "\tFIELD KIND task|path\n\t\tREQUIRED\n"
    "\tFIELD CONDITION string\n\t\tREQUIRED\n"
    "\tFIELD GLOB glob\n\t\tREPEATABLE\n"
    "\tFIELD LOADS @RULE\n\t\tREPEATABLE\n"
    "\n"
    "SCHEMA RULE\n"
    '\tDESC "a rule"\n'
    "\tFIELD SPEC string\n\t\tREQUIRED\n"
)
INSTRUCTIONS_TRIGGERS = (
    'TRIGGER cart_code\n\tKIND path\n\tCONDITION "a file of the cart"\n\tGLOB "src/cart/**"\n'
    "\tLOADS @RULE.cart_is_pure\n\n"
    'TRIGGER billing_code\n\tKIND path\n\tCONDITION "a file of the billing"\n\tGLOB "src/billing/**"\n'
    "\tLOADS @RULE.charges_are_logged\n\n"
    'TRIGGER shipping_code\n\tKIND path\n\tCONDITION "a file of the shipping"\n\tGLOB "src/shipping/**"\n'
    "\tLOADS @RULE.parcels_are_weighed\n\n"
    'TRIGGER changing_code\n\tKIND task\n\tCONDITION "changing code"\n\tLOADS @RULE.cart_is_pure\n\n'
    'TRIGGER cart_button_code\n\tKIND path\n\tCONDITION "the button of the cart"\n\tGLOB "src/cart/button.py"\n'
    "\tLOADS @RULE.cart_is_pure\n\n"
    'RULE cart_is_pure\n\tSPEC "the cart computes without input or output"\n\n'
    'RULE charges_are_logged\n\tSPEC "every charge is logged"\n\n'
    'RULE parcels_are_weighed\n\tSPEC "every parcel is weighed"\n'
)
FAKE_CLIENT = 'client = "fake"\n{keys}[clients.fake]\nrecordings = "{recordings}"\n{settings}'
RUN_ID = "20261016T120000Z-a1b2c3"


class TaskContextTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        root = Path(self.root.name).resolve()
        self.machine = TemporaryMachine(root)
        self.state = self.machine.state_home / "brigade"
        self.recordings = root / "recordings"
        self.recordings.mkdir()
        self.machine.install_awawa(self)
        self.machine.run_init()
        self.configure()
        self.project = TemporaryProject(root / "projects" / "shop", self.describe_environment())
        self.project.write("corpus/_schema.awawa", PROJECT_SCHEMA)
        self.project.write("corpus/tasks.awawa", MAIN_TASKS)
        self.project.track("corpus")
        self.project.run_git("commit", "--quiet", "-m", "the corpus")
        self.project.run_git("checkout", "--quiet", "-b", WAVE_BRANCH)
        self.project.write("corpus/tasks.awawa", WAVE_TASKS)
        self.project.write("corpus/milestones.awawa", WAVE_MILESTONES)
        self.project.track("corpus")
        self.project.run_git("commit", "--quiet", "-m", "the plan of M1")
        self.project.run_git("checkout", "--quiet", "main")
        self.machine.run_brigade(
            CLONE_ENTRY_POINT,
            "project",
            "add",
            str(self.project.path),
            *self.describe_project_commands(),
        )
        self.wave_started = self.state / "ledger" / "2026-10.jsonl"
        self.wave_started.parent.mkdir(parents=True)
        self.wave_started.write_text(WAVE_STARTED)
        self.worktree = self.project.path / ".brigade" / "worktrees" / "S3"
        self.project.run_git("worktree", "add", "--quiet", "-b", TASK_BRANCH, str(self.worktree), WAVE_BRANCH)
        self.setup_log = self.state / "setups" / "shop" / "S3.log"
        self.setup_log.parent.mkdir(parents=True)
        self.setup_log.write_text(SETUP_LOG)

    def tearDown(self):
        self.root.cleanup()

    def describe_environment(self) -> dict:
        return {**self.machine.describe_environment(), **PINNED_COMMIT_DATES}

    def describe_project_commands(self) -> tuple[str, ...]:
        return ("--acceptance", ACCEPTANCE_COMMAND, "--heavy", HEAVY_COMMAND)

    def configure(self, keys: str = "", settings: str = "") -> None:
        self.machine.write_configuration(FAKE_CLIENT.format(keys=keys, recordings=self.recordings, settings=settings))

    def run_task_context(self, *arguments: str, cwd: Path | None = None, environment: dict | None = None):
        return self.machine.run_brigade(
            CLONE_ENTRY_POINT,
            "task",
            "context",
            *arguments,
            environment=environment or self.describe_environment(),
            cwd=cwd or self.worktree,
        )

    def read_document(self, *arguments: str, environment: dict | None = None) -> dict:
        completed = self.run_task_context("--json", *arguments, environment=environment)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def describe_run_environment(self) -> dict:
        return {**self.describe_environment(), "BRIGADE_RUN_DIR": str(self.state / "runs" / RUN_ID)}


class BrigadeTaskContextInTheWorktreeOfATaskTest(TaskContextTestCase):
    def test_should_print_every_section_of_the_package_as_a_versioned_document(self):
        # Act
        document = self.read_document()

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "worktree": {
                    "ancestry": {
                        "command": f"git merge-base --is-ancestor {WAVE_BRANCH} HEAD",
                        "exit_code": 0,
                    },
                    "setup": SETUP_LOG,
                },
                "task": [
                    {"command": "awawa context @TASK.S3 --with-schema .", "exit_code": 0, "stderr": "", "output": ANY},
                    {"command": "awawa lint --closure @TASK.S3 .", "exit_code": 0, "stderr": "", "output": ANY},
                ],
                "rules": None,
                "project": None,
                "acceptance": {"acceptance": [ACCEPTANCE_COMMAND], "heavy": [HEAVY_COMMAND]},
                "reserved": {"task_number": 7, "temporary_directory": None, "attribution": []},
                "when_done": ["brigade task check", "brigade task pr", "brigade task promote"],
            },
        )

    def test_should_print_the_task_read_from_the_branch_of_the_worktree_under_its_command_line(self):
        # Act
        completed = self.run_task_context()

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("$ awawa context @TASK.S3 --with-schema .\nexit 0\nTASK S3\n", completed.stdout)

    def test_should_print_the_closure_of_the_task_under_its_command_line(self):
        # Act
        completed = self.run_task_context()

        # Assert
        self.assertIn("$ awawa lint --closure @TASK.S3 .\nexit 0\n", completed.stdout)

    def test_should_accept_the_task_of_the_branch_named_as_its_argument(self):
        # Act
        completed = self.run_task_context("S3")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_should_print_the_ancestry_and_the_setup_under_the_worktree_section(self):
        # Act
        completed = self.run_task_context()

        # Assert
        self.assertIn(
            f"# worktree\n$ git merge-base --is-ancestor {WAVE_BRANCH} HEAD\nexit 0\n{SETUP_LOG}",
            completed.stdout,
        )

    def test_should_print_the_acceptance_commands_then_the_heavy_ones_left_to_ci(self):
        # Act
        completed = self.run_task_context()

        # Assert
        self.assertIn(
            f"# acceptance\n{ACCEPTANCE_COMMAND}\n{HEAVY_COMMAND}  (left to CI)\n",
            completed.stdout,
        )

    def test_should_end_on_the_commands_to_run_once_the_task_is_done(self):
        # Act
        completed = self.run_task_context()

        # Assert
        self.assertRegex(
            completed.stdout, r"# when done\nbrigade task check\nbrigade task pr\nbrigade task promote\n\Z"
        )

    def test_should_write_no_package_and_no_temporary_directory_outside_a_run(self):
        # Act
        self.run_task_context()

        # Assert
        self.assertFalse((self.state / "runs").exists())


class BrigadeTaskContextOutsideTheWorktreeOfATaskTest(TaskContextTestCase):
    def test_should_exit_1_naming_the_branch_that_is_not_a_task_branch(self):
        # Act
        completed = self.run_task_context(cwd=self.project.path)

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout, completed.stderr),
            (1, "", "brigade task context: the branch main is not a task/<slug>/<task> branch\n"),
        )

    def test_should_exit_1_naming_a_task_other_than_the_task_of_the_branch(self):
        # Act
        completed = self.run_task_context("S6")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout, completed.stderr),
            (1, "", f"brigade task context: @TASK.S6 is not the task of the branch {TASK_BRANCH}\n"),
        )


class BrigadeTaskContextOfATaskTheCorpusDoesNotHoldTest(TaskContextTestCase):
    def setUp(self):
        super().setUp()
        self.worktree = self.project.path / ".brigade" / "worktrees" / "S7"
        self.project.run_git(
            "worktree", "add", "--quiet", "-b", "task/M1-empty-cart/S7", str(self.worktree), WAVE_BRANCH
        )

    def test_should_exit_1_naming_the_task(self):
        # Act
        completed = self.run_task_context()

        # Assert
        self.assertEqual((completed.returncode, completed.stdout), (1, ""))
        self.assertRegex(
            completed.stderr, r"\Abrigade task context: awawa context @TASK\.S7 --with-schema \. exited 1: "
        )


class BrigadeTaskContextOfAWorktreeWhoseCorpusRepeatsAMilestoneTest(TaskContextTestCase):
    def setUp(self):
        super().setUp()
        (self.worktree / "corpus" / "again.awawa").write_text(REPEATED_MILESTONE)

    def test_should_print_what_awawa_writes_on_stderr(self):
        # Act
        document = self.read_document()

        # Assert
        self.assertIn("duplicate identity @MILESTONE.M1", document["task"][0]["stderr"])

    def test_should_print_the_exit_code_of_the_closure_that_finds_an_error(self):
        # Act
        document = self.read_document()

        # Assert
        self.assertEqual(document["task"][1]["exit_code"], 1)

    def test_should_print_the_exit_code_then_the_stderr_under_the_command_line(self):
        # Act
        completed = self.run_task_context()

        # Assert
        self.assertRegex(completed.stdout, r"\$ awawa context @TASK\.S3 --with-schema \.\nexit 0\nL005 ")


class BrigadeTaskContextOfABranchNoWaveStartedTest(TaskContextTestCase):
    def setUp(self):
        super().setUp()
        self.worktree = self.project.path / ".brigade" / "worktrees" / "S6"
        self.project.run_git("worktree", "add", "--quiet", "-b", "task/M2-gift-wrap/S6", str(self.worktree), "main")

    def test_should_exit_1_naming_the_wave_branch_no_wave_started_names(self):
        # Act
        completed = self.run_task_context()

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout, completed.stderr),
            (1, "", "brigade task context: no wave.started of @PROJECT.shop has the branch integration/M2-gift-wrap\n"),
        )


class BrigadeTaskContextInARepositoryNoProjectRegistersTest(TaskContextTestCase):
    def setUp(self):
        super().setUp()
        self.pantry = TemporaryProject(
            Path(self.root.name).resolve() / "projects" / "pantry", self.describe_environment()
        )
        self.pantry.run_git("commit", "--quiet", "--allow-empty", "-m", "the pantry")
        self.pantry.run_git("checkout", "--quiet", "-b", TASK_BRANCH)

    def test_should_exit_1_naming_the_repository(self):
        # Act
        completed = self.run_task_context(cwd=self.pantry.path)

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout, completed.stderr),
            (1, "", f"brigade task context: no registered project at {self.pantry.path}\n"),
        )


class BrigadeTaskContextWithNoClientConfiguredTest(TaskContextTestCase):
    def setUp(self):
        super().setUp()
        self.machine.write_configuration("")

    def test_should_print_no_attribution_line(self):
        # Act
        document = self.read_document()

        # Assert
        self.assertEqual(document["reserved"]["attribution"], [])


class BrigadeTaskContextOfAWorktreeCutByHandTest(TaskContextTestCase):
    def setUp(self):
        super().setUp()
        self.setup_log.unlink()

    def test_should_print_no_setup(self):
        # Act
        document = self.read_document()

        # Assert
        self.assertIsNone(document["worktree"]["setup"])


class BrigadeTaskContextAfterTheWaveMovedTest(TaskContextTestCase):
    def setUp(self):
        super().setUp()
        self.project.run_git("checkout", "--quiet", WAVE_BRANCH)
        self.project.write("corpus/tasks.awawa", f"{WAVE_TASKS}\n{TASK_ADDED_ON_THE_WAVE}")
        self.project.track("corpus")
        self.project.run_git("commit", "--quiet", "-m", "S9 joins the wave")
        self.project.run_git("checkout", "--quiet", "main")

    def test_should_print_the_exit_code_of_the_ancestry_of_the_wave_branch(self):
        # Act
        document = self.read_document()

        # Assert
        self.assertEqual(
            document["worktree"]["ancestry"],
            {"command": f"git merge-base --is-ancestor {WAVE_BRANCH} HEAD", "exit_code": 1},
        )

    def test_should_reserve_the_number_above_the_highest_of_the_corpus_at_the_wave_branch(self):
        # Act
        document = self.read_document()

        # Assert
        self.assertEqual(document["reserved"]["task_number"], 10)


class BrigadeTaskContextAfterANumberWasReservedTest(TaskContextTestCase):
    def setUp(self):
        super().setUp()
        self.read_document()

    def test_should_reserve_the_number_above_the_one_already_reserved_for_the_project(self):
        # Act
        document = self.read_document()

        # Assert
        self.assertEqual(document["reserved"]["task_number"], 8)


class BrigadeTaskContextOfAProjectWithAgentsInstructionsTest(TaskContextTestCase):
    def setUp(self):
        super().setUp()
        (self.worktree / "AGENTS.md").write_text(AGENTS_TEXT)

    def test_should_print_the_text_of_the_agents_file_of_the_worktree(self):
        # Act
        document = self.read_document()

        # Assert
        self.assertEqual(document["project"], AGENTS_TEXT)

    def test_should_print_the_agents_file_under_the_project_section(self):
        # Act
        completed = self.run_task_context()

        # Assert
        self.assertIn(f"# project\n{AGENTS_TEXT}", completed.stdout)

    def test_should_read_the_agents_file_at_the_root_of_the_worktree_from_one_of_its_directories(self):
        # Arrange
        directory_of_the_worktree = self.worktree / "corpus"

        # Act
        completed = self.run_task_context("--json", cwd=directory_of_the_worktree)

        # Assert
        self.assertEqual(json.loads(completed.stdout)["project"], AGENTS_TEXT)


class BrigadeTaskContextWithAnInstructionsCorpusTest(TaskContextTestCase):
    def setUp(self):
        super().setUp()
        self.instructions = Path(self.root.name).resolve() / "instructions"
        self.instructions.mkdir()
        (self.instructions / "_schema.awawa").write_text(INSTRUCTIONS_SCHEMA)
        (self.instructions / "triggers.awawa").write_text(INSTRUCTIONS_TRIGGERS)
        self.configure(keys=f'instructions = "{self.instructions}"\n')

    def test_should_print_the_path_triggers_whose_glob_matches_a_path_of_the_task(self):
        # Act
        document = self.read_document()

        # Assert
        self.assertEqual(
            document["rules"],
            [
                {
                    "trigger": "cart_code",
                    "command": f"awawa context @TRIGGER.cart_code --depth 1 --skip reasoning {self.instructions}",
                    "exit_code": 0,
                    "stderr": "",
                    "output": ANY,
                },
                {
                    "trigger": "billing_code",
                    "command": f"awawa context @TRIGGER.billing_code --depth 1 --skip reasoning {self.instructions}",
                    "exit_code": 0,
                    "stderr": "",
                    "output": ANY,
                },
                {
                    "trigger": "cart_button_code",
                    "command": (
                        f"awawa context @TRIGGER.cart_button_code --depth 1 --skip reasoning {self.instructions}"
                    ),
                    "exit_code": 0,
                    "stderr": "",
                    "output": ANY,
                },
            ],
        )

    def test_should_print_the_rules_each_trigger_loads(self):
        # Act
        document = self.read_document()

        # Assert
        self.assertIn("RULE cart_is_pure\n", document["rules"][0]["output"])

    def test_should_print_the_matching_triggers_under_the_rules_section(self):
        # Act
        completed = self.run_task_context()

        # Assert
        self.assertIn(
            f"# rules\n$ awawa context @TRIGGER.cart_code --depth 1 --skip reasoning {self.instructions}\nexit 0\n",
            completed.stdout,
        )


class BrigadeTaskContextInARunTest(TaskContextTestCase):
    def setUp(self):
        super().setUp()
        self.run_directory = self.state / "runs" / RUN_ID
        self.run_directory.mkdir(parents=True)

    def test_should_reserve_the_temporary_directory_of_the_run(self):
        # Act
        document = self.read_document(environment=self.describe_run_environment())

        # Assert
        self.assertEqual(document["reserved"]["temporary_directory"], str(self.run_directory / "tmp"))

    def test_should_create_the_temporary_directory_of_the_run(self):
        # Act
        self.run_task_context(environment=self.describe_run_environment())

        # Assert
        self.assertTrue((self.run_directory / "tmp").is_dir())

    def test_should_write_the_package_it_prints_to_the_run_directory(self):
        # Act
        completed = self.run_task_context(environment=self.describe_run_environment())

        # Assert
        self.assertEqual((self.run_directory / "context.md").read_text(), completed.stdout)


class BrigadeTaskContextOfAClientAnsweringAnAttributionTest(TaskContextTestCase):
    def setUp(self):
        super().setUp()
        self.configure(settings='attribution = "Co-Authored-By: Fake Model <fake@example.org>,Session: 42"\n')

    def test_should_print_the_attribution_lines_the_probe_of_the_client_answers(self):
        # Act
        document = self.read_document()

        # Assert
        self.assertEqual(
            document["reserved"]["attribution"], ["Co-Authored-By: Fake Model <fake@example.org>", "Session: 42"]
        )

    def test_should_print_the_attribution_lines_of_the_configuration_in_their_place(self):
        # Arrange
        self.configure(
            keys='attribution = ["Co-Authored-By: Ada <ada@example.org>", "Session: 42"]\n',
            settings='attribution = "Co-Authored-By: Fake Model <fake@example.org>"\n',
        )

        # Act
        document = self.read_document()

        # Assert
        self.assertEqual(document["reserved"]["attribution"], ["Co-Authored-By: Ada <ada@example.org>", "Session: 42"])

    def test_should_print_the_attribution_lines_under_the_reserved_section(self):
        # Act
        completed = self.run_task_context()

        # Assert
        self.assertIn(
            "# reserved\ntask number 7\nCo-Authored-By: Fake Model <fake@example.org>\nSession: 42\n", completed.stdout
        )
