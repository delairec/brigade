import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import ANY

from tests.awawa.provide_awawa import provide_awawa
from tests.cli.run_test_case import FileWaitingTestCase
from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine
from tests.cli.temporary_project import PINNED_COMMIT_DATES, TemporaryProject

PROJECT_SCHEMA = (
    "SCHEMA TASK\n"
    '\tDESC "a change delivered by one pull request"\n'
    "\tFIELD TITLE string\n\t\tREQUIRED\n"
    "\tFIELD STATUS todo|implemented\n\t\tREQUIRED\n"
    "\tFIELD AFTER @TASK\n\t\tREPEATABLE\n"
    "\n"
    "SCHEMA OPEN_QUESTION\n"
    '\tDESC "a fact left undecided"\n'
    "\tFIELD STATUS open|closed\n\t\tREQUIRED\n"
    "\tFIELD BLOCKS @TASK\n\t\tREPEATABLE\n\t\tCONVERSE BLOCKED_BY\n"
    "\tWHEN STATUS closed\n\t\tGATE suppressed\n"
)
MAIN_TASKS = (
    'TASK S2\n\tTITLE "Remove an item from the cart"\n\tSTATUS implemented\n\n'
    'TASK S3\n\tTITLE "Empty the cart in one click"\n\tSTATUS todo\n\tAFTER @TASK.S2\n\n'
    'TASK S4\n\tTITLE "Confirm before emptying the cart"\n\tSTATUS todo\n\tAFTER @TASK.S3\n\n'
    'TASK S5\n\tTITLE "Undo the emptying"\n\tSTATUS todo\n\tAFTER @TASK.S6\n\n'
    'TASK S6\n\tTITLE "Keep the emptied cart for a day"\n\tSTATUS todo\n\n'
    'TASK S7\n\tTITLE "Count the emptied carts"\n\tSTATUS todo\n\n'
    'TASK S10\n\tTITLE "Show the emptied cart"\n\tSTATUS todo\n\n'
    'TASK Cleanup\n\tTITLE "Tidy the cart module"\n\tSTATUS todo\n'
)
MAIN_QUESTIONS = "OPEN_QUESTION KeepDuration\n\tSTATUS open\n\tBLOCKS @TASK.S6\n"
PLAN_TASKS = 'TASK S11\n\tTITLE "Share the cart"\n\tSTATUS todo\n'
OPEN_WAVE = (
    '{"schema_version": 2, "ts": "2026-10-13T09:00:00Z", "event": "wave.started", "wave": "shop_w1",'
    ' "project": "shop", "branch": "integration/shop_w1", "tasks": ["S7"]}\n'
)
CANCELLED_WAVE = (
    '{"schema_version": 1, "ts": "2026-10-13T10:00:00Z", "event": "wave.cancelled", "wave": "shop_w1",'
    ' "reason": "user"}\n'
)
CLOSED_WAVE = (
    '{"schema_version": 1, "ts": "2026-10-13T10:00:00Z", "event": "wave.closed", "wave": "shop_w1", "pr": 31}\n'
)
STARTED_WAVE = {
    "schema_version": 1,
    "wave": "shop_w2",
    "project": "shop",
    "branch": "integration/shop_w2",
    "tasks": ["S3", "S4", "S10"],
}


class WaveStartTestCase(FileWaitingTestCase):
    def setUp(self):
        provide_awawa(self)
        self.root = tempfile.TemporaryDirectory()
        root = Path(self.root.name).resolve()
        self.machine = TemporaryMachine(root)
        self.machine.run_init()
        self.project = TemporaryProject(
            root / "projects" / "shop", {**self.machine.describe_environment(), **PINNED_COMMIT_DATES}
        )
        self.project.write("corpus/_schema.awawa", PROJECT_SCHEMA)
        self.project.write("corpus/tasks.awawa", MAIN_TASKS)
        self.project.write("corpus/questions.awawa", MAIN_QUESTIONS)
        self.project.track("corpus")
        self.project.run_git("commit", "--quiet", "-m", "the corpus")
        self.machine.run_brigade(CLONE_ENTRY_POINT, "project", "add", str(self.project.path))
        self.ledger = self.machine.state_home / "brigade" / "ledger"
        self.ledger.mkdir(parents=True)
        (self.ledger / "2026-10.jsonl").write_text(OPEN_WAVE)

    def tearDown(self):
        self.root.cleanup()

    def run_wave_start(self, *arguments: str):
        return self.machine.run_brigade(CLONE_ENTRY_POINT, "wave", "start", *arguments)

    def read_events(self, name: str) -> list:
        lines = "".join(path.read_text() for path in sorted(self.ledger.glob("*.jsonl"))).splitlines()
        return [event for event in map(json.loads, lines) if event["event"] == name]

    def use_a_github_remote(self) -> Path:
        remote = Path(self.root.name).resolve() / "remote.git"
        self.project.run_git("init", "--quiet", "--bare", str(remote))
        self.project.run_git("remote", "add", "origin", str(remote))
        projects = self.machine.corpus / "projects.awawa"
        projects.write_text(projects.read_text().replace('\tFORGE "none"\n', '\tFORGE "github"\n'))
        return remote


class BrigadeWaveStartTest(WaveStartTestCase):
    def test_should_compose_the_wave_from_the_startable_tasks_in_the_order_of_their_number(self):
        # Act
        completed = self.run_wave_start("shop", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout), STARTED_WAVE)

    def test_should_record_the_start_of_the_wave_in_the_ledger(self):
        # Act
        self.run_wave_start("shop")

        # Assert
        self.assertEqual(
            self.read_events("wave.started")[-1],
            {
                "schema_version": 2,
                "ts": ANY,
                "event": "wave.started",
                "wave": "shop_w2",
                "project": "shop",
                "branch": "integration/shop_w2",
                "tasks": ["S3", "S4", "S10"],
            },
        )

    def test_should_cut_the_integration_branch_from_the_main_branch(self):
        # Act
        self.run_wave_start("shop")

        # Assert
        self.assertEqual(
            self.project.run_git("rev-parse", "integration/shop_w2"), self.project.run_git("rev-parse", "main")
        )

    def test_should_cut_the_missing_branch_of_an_open_wave_without_a_second_wave_started(self):
        # Act
        self.run_wave_start("shop")

        # Assert
        self.assertEqual(
            self.project.run_git("rev-parse", "integration/shop_w1"), self.project.run_git("rev-parse", "main")
        )
        self.assertEqual([event["wave"] for event in self.read_events("wave.started")], ["shop_w1", "shop_w2"])

    def test_should_start_a_wave_beside_an_open_wave_whose_branch_exists(self):
        # Arrange
        self.run_wave_start("shop", "--task", "S3")

        # Act
        completed = self.run_wave_start("shop", "--task", "S10")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout),
            (0, "wave shop_w3 of @PROJECT.shop on integration/shop_w3: S10\n"),
        )

    def test_should_take_the_tasks_of_a_cancelled_wave_again(self):
        # Arrange
        (self.ledger / "2026-10.jsonl").write_text(OPEN_WAVE + CANCELLED_WAVE)

        # Act
        completed = self.run_wave_start("shop", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["tasks"], ["S3", "S4", "S7", "S10"])

    def test_should_leave_the_missing_branch_of_a_closed_wave_uncut(self):
        # Arrange
        (self.ledger / "2026-10.jsonl").write_text(OPEN_WAVE + CLOSED_WAVE)

        # Act
        self.run_wave_start("shop")

        # Assert
        self.assertEqual(self.project.run_git("branch", "--list", "integration/shop_w1"), "")

    def test_should_take_no_task_of_a_plan_not_yet_in_the_main_branch(self):
        # Arrange
        self.project.run_git("switch", "--quiet", "--create", "plan/shop_r1")
        self.project.write("corpus/plan.awawa", PLAN_TASKS)
        self.project.track("corpus")
        self.project.run_git("commit", "--quiet", "-m", "the plan of shop_r1")
        self.project.run_git("switch", "--quiet", "main")

        # Act
        completed = self.run_wave_start("shop", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["tasks"], ["S3", "S4", "S10"])

    def test_should_print_the_wave_as_text(self):
        # Act
        completed = self.run_wave_start("shop")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout),
            (0, "wave shop_w2 of @PROJECT.shop on integration/shop_w2: S3, S4, S10\n"),
        )

    def test_should_exit_1_naming_the_project_when_no_task_is_left_to_start(self):
        # Arrange
        self.run_wave_start("shop")

        # Act
        completed = self.run_wave_start("shop")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stderr),
            (1, "brigade wave start: @PROJECT.shop has no task to start\n"),
        )


class BrigadeWaveStartOfNamedTasksTest(WaveStartTestCase):
    def test_should_take_exactly_the_named_tasks(self):
        # Act
        completed = self.run_wave_start("shop", "--task", "S4", "--task", "S3", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["tasks"], ["S3", "S4"])

    def test_should_exit_1_naming_the_refused_task_before_any_write(self):
        for task, expected_stderr in [
            ("S7", "brigade wave start: @TASK.S7 is in the open wave shop_w1\n"),
            ("Cleanup", "brigade wave start: @TASK.Cleanup has no number in its name\n"),
            ("S4", "brigade wave start: @TASK.S4 comes after @TASK.S3, neither implemented nor named\n"),
            ("S99", "brigade wave start: @TASK.S99 is not defined in the corpus of @PROJECT.shop\n"),
        ]:
            with self.subTest(task=task):
                # Act
                completed = self.run_wave_start("shop", "--task", task)

                # Assert
                self.assertEqual((completed.returncode, completed.stderr), (1, expected_stderr))
                self.assertEqual([event["wave"] for event in self.read_events("wave.started")], ["shop_w1"])


class BrigadeWaveStartOnABranchNoWaveStartedNamesTest(WaveStartTestCase):
    def test_should_exit_1_naming_a_local_branch_of_the_name(self):
        # Arrange
        self.project.run_git("branch", "integration/shop_w2")

        # Act
        completed = self.run_wave_start("shop")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stderr),
            (1, "brigade wave start: the branch integration/shop_w2 exists and no wave.started names it\n"),
        )
        self.assertEqual([event["wave"] for event in self.read_events("wave.started")], ["shop_w1"])

    def test_should_exit_1_naming_a_remote_branch_of_the_name(self):
        # Arrange
        self.use_a_github_remote()
        self.project.run_git("push", "--quiet", "origin", "main:integration/shop_w2")

        # Act
        completed = self.run_wave_start("shop")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stderr),
            (1, "brigade wave start: the branch integration/shop_w2 exists and no wave.started names it\n"),
        )


class BrigadeWaveStartOnAProjectOfTheGithubForgeTest(WaveStartTestCase):
    def test_should_push_the_integration_branch(self):
        # Arrange
        self.use_a_github_remote()

        # Act
        completed = self.run_wave_start("shop")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("refs/heads/integration/shop_w2", self.project.run_git("ls-remote", "--heads", "origin"))


class BrigadeWaveStartBeforeInitTest(unittest.TestCase):
    def setUp(self):
        provide_awawa(self)
        self.root = tempfile.TemporaryDirectory()
        self.machine = TemporaryMachine(Path(self.root.name).resolve())

    def tearDown(self):
        self.root.cleanup()

    def test_should_exit_1_naming_brigade_init(self):
        # Act
        completed = self.machine.run_brigade(CLONE_ENTRY_POINT, "wave", "start", "shop")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stderr),
            (1, "brigade wave start: the operational corpus is missing; run brigade init first\n"),
        )


if __name__ == "__main__":
    unittest.main()
