import tempfile
import unittest
from pathlib import Path

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
WAVE_MILESTONES = 'MILESTONE M1\n\tTITLE "Empty cart"\n\tSTATUS running\n'
WAVE_BRANCH = "integration/M1-empty-cart"
TASK_BRANCH = "task/M1-empty-cart/S3"
WAVE_STARTED = (
    '{"schema_version": 2, "ts": "2026-10-13T09:00:00Z", "event": "wave.started", "wave": "shop_w1",'
    f' "project": "shop", "branch": "{WAVE_BRANCH}", "tasks": ["S3", "S6"]}}\n'
)
ACCEPTANCE_COMMAND = "python3 -m unittest"
HEAVY_COMMAND = "python3 -m unittest discover tests/e2e"
SETUP_LOG = "$ touch setup-ran\n"
FAKE_CLIENT = 'client = "fake"\n{keys}[clients.fake]\nrecordings = "{recordings}"\n{settings}'


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

    def run_task_context(self):
        return self.machine.run_brigade(
            CLONE_ENTRY_POINT, "task", "context", environment=self.describe_environment(), cwd=self.worktree
        )


class BrigadeTaskContextInTheWorktreeOfATaskTest(TaskContextTestCase):
    def test_should_print_the_package_of_the_task_of_the_branch_section_by_section(self):
        # Act
        completed = self.run_task_context()

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stderr, "")
        self.assertRegex(
            completed.stdout,
            r"\A# worktree\n\$ git merge-base --is-ancestor integration/M1-empty-cart HEAD\nexit 0\n"
            r"\$ touch setup-ran\n\n"
            r"# task\n\$ awawa context @TASK\.S3 --with-schema \.\nexit 0\nTASK S3\n(?s:.*)"
            r"\$ awawa lint --closure @TASK\.S3 \.\nexit 0\n(?s:.*)\n"
            r"# acceptance\npython3 -m unittest\npython3 -m unittest discover tests/e2e  \(left to CI\)\n\n"
            r"# reserved\ntask number 7\n\n"
            r"# when done\nbrigade task check\nbrigade task pr\nbrigade task promote\n\Z",
        )
