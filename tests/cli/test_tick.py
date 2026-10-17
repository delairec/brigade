import fcntl
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import ANY

from tests.awawa.provide_awawa import provide_awawa
from tests.cli.run_test_case import COUNTING_CLIENT, DONE_RESULT, FileWaitingTestCase
from tests.cli.temporary_machine import CLONE_ENTRY_POINT, TemporaryMachine
from tests.cli.temporary_project import PINNED_COMMIT_DATES, TemporaryProject
from tests.process_launcher import ProcessLauncher

INSTANT = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
STOP_WAIT_S = 10
CLIENT_OUTLIVING_THE_TEST = 'delay = "120"\n'
PROJECT_SCHEMA = (
    "SCHEMA TASK\n"
    '\tDESC "a change delivered by one pull request"\n'
    "\tFIELD TITLE string\n\t\tREQUIRED\n"
    "\tFIELD STATUS todo|implemented\n\t\tREQUIRED\n"
    "\tFIELD MILESTONE @MILESTONE\n"
    "\tFIELD AFTER @TASK\n\t\tREPEATABLE\n"
    "\n"
    "SCHEMA MILESTONE\n"
    '\tDESC "the tasks planned for one request"\n'
    "\tFIELD TITLE string\n\t\tREQUIRED\n"
    "\tFIELD STATUS planned|running\n\t\tREQUIRED\n"
    "\n"
    "SCHEMA OPEN_QUESTION\n"
    '\tDESC "a fact left undecided"\n'
    "\tFIELD STATUS open|closed\n\t\tREQUIRED\n"
    "\tFIELD BLOCKS @TASK\n\t\tREPEATABLE\n\t\tCONVERSE BLOCKED_BY\n"
    "\tWHEN STATUS closed\n\t\tGATE suppressed\n"
)
MAIN_TASKS = 'TASK S2\n\tTITLE "Remove an item from the cart"\n\tSTATUS implemented\n'
WAVE_TASKS = (
    'TASK S2\n\tTITLE "Remove an item from the cart"\n\tSTATUS implemented\n\n'
    'TASK S3\n\tTITLE "Empty the cart in one click"\n\tSTATUS todo\n\tMILESTONE @MILESTONE.M1\n\tAFTER @TASK.S2\n\n'
    'TASK S4\n\tTITLE "Confirm before emptying the cart"\n\tSTATUS todo\n\tMILESTONE @MILESTONE.M1\n'
    "\tAFTER @TASK.S3\n\n"
    'TASK S5\n\tTITLE "Undo the emptying"\n\tSTATUS todo\n\tMILESTONE @MILESTONE.M1\n\n'
    'TASK S6\n\tTITLE "Count the emptied carts"\n\tSTATUS todo\n\tMILESTONE @MILESTONE.M1\n'
)
WAVE_MILESTONES = 'MILESTONE M1\n\tTITLE "Empty cart"\n\tSTATUS running\n'
WAVE_QUESTIONS = (
    "OPEN_QUESTION Undecided\n\tSTATUS open\n\tBLOCKS @TASK.S5\n\n"
    "OPEN_QUESTION Ruled\n\tSTATUS closed\n\tBLOCKS @TASK.S6\n"
)
WAVE_BRANCH = "integration/M1-empty-cart"
RUNNING_REQUEST = (
    "REQUEST shop_1\n"
    "\tPROJECT @PROJECT.shop\n"
    '\tTEXT "let the customer empty the cart in one click"\n'
    '\tCREATED_AT "2026-10-12T09:30:00Z"\n'
    "\tSTATUS running\n"
    '\tMILESTONE "M1"\n'
    f'\tBRANCH "{WAVE_BRANCH}"\n'
)
PLANNED_WAVE_REQUEST = (
    "REQUEST shop_1\n"
    "\tPROJECT @PROJECT.shop\n"
    '\tTEXT "let the customer empty the cart in one click"\n'
    '\tCREATED_AT "2026-10-12T09:30:00Z"\n'
    "\tSTATUS planned\n"
    '\tMILESTONE "M1"\n'
    f'\tBRANCH "{WAVE_BRANCH}"\n'
)
PLANNED_REQUEST = (
    "REQUEST shop_2\n"
    "\tPROJECT @PROJECT.shop\n"
    '\tTEXT "let the customer undo the emptying"\n'
    '\tCREATED_AT "2026-10-12T10:30:00Z"\n'
    "\tSTATUS planned\n"
    '\tMILESTONE "M2"\n'
    '\tBRANCH "integration/M2-undo"\n'
)
QUEUED_S3 = (
    '{"schema_version": 1, "ts": "2026-10-13T10:00:00Z", "event": "task.state", "wave": "M1", "task": "S3",'
    ' "state": "queued"}\n'
)


class TickTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.machine = TemporaryMachine(Path(self.root.name).resolve())
        self.state = self.machine.state_home / "brigade"
        self.heartbeat = self.state / "tick.json"
        self.lock = self.state / "locks" / "tick.lock"

    def tearDown(self):
        self.root.cleanup()

    def run_tick(self, *options: str):
        return self.machine.run_brigade(CLONE_ENTRY_POINT, "tick", *options)

    def hold_tick_lock(self) -> None:
        self.lock.parent.mkdir(parents=True)
        holder = self.enterContext(self.lock.open("a"))
        fcntl.flock(holder, fcntl.LOCK_EX)

    def start_loop(self, *options: str) -> subprocess.Popen:
        loop = ProcessLauncher.start(
            [sys.executable, str(CLONE_ENTRY_POINT), "tick", "--loop", *options],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self.machine.describe_environment(),
        )
        self.addCleanup(loop.kill)
        return loop

    def wait_for_first_tick(self, loop: subprocess.Popen) -> str:
        return loop.stderr.readline()


class BrigadeTickOnceTest(TickTestCase):
    def test_should_write_the_heartbeat_of_a_tick_that_applied_no_action(self):
        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        heartbeat = json.loads(self.heartbeat.read_text())
        self.assertRegex(heartbeat["ts"], INSTANT)
        self.assertIsInstance(heartbeat["duration_ms"], int)
        self.assertEqual(heartbeat, {"schema_version": 1, "ts": ANY, "duration_ms": ANY, "actions_applied": 0})

    def test_should_leave_the_lock_the_heartbeat_and_the_trails_alone_in_the_state_directory(self):
        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(sorted(path.name for path in self.state.iterdir()), ["locks", "tick.json", "ticks"])

    def test_should_report_the_tick_it_recorded_in_the_versioned_document(self):
        # Act
        completed = self.run_tick("--once", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        heartbeat = json.loads(self.heartbeat.read_text())
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "schema_version": 1,
                "mode": "once",
                "ts": heartbeat["ts"],
                "duration_ms": heartbeat["duration_ms"],
                "actions_applied": 0,
                "heartbeat": str(self.heartbeat),
            },
        )

    def test_should_print_the_tick_as_text(self):
        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertRegex(
            completed.stdout, r"^tick \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z: 0 actions applied in \d+ ms\n$"
        )


class BrigadeTickOnceWhileAnotherTickHoldsTheLockTest(TickTestCase):
    def test_should_exit_0_with_one_stderr_line_and_write_nothing(self):
        # Arrange
        self.hold_tick_lock()

        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout, completed.stderr),
            (0, "", f"brigade tick: another tick holds {self.lock}\n"),
        )
        self.assertEqual(list(self.state.iterdir()), [self.state / "locks"])


BUILD_PROCEDURE = "---\ncapabilities: read, write, shell\nbudget: 75\n---\nDeliver the task.\n"
TASK_BRANCH = "task/M1-empty-cart/S3"


class WaveTickTestCase(TickTestCase):
    setup_commands = ("touch setup-ran",)

    def run_tick(self, *options: str):
        return self.machine.run_brigade(
            CLONE_ENTRY_POINT,
            "tick",
            *options,
            environment={**self.machine.describe_environment(), **PINNED_COMMIT_DATES},
        )

    def setUp(self):
        super().setUp()
        provide_awawa(self)
        self.machine.run_init()
        self.project = TemporaryProject(
            Path(self.root.name).resolve() / "projects" / "shop",
            {**self.machine.describe_environment(), **PINNED_COMMIT_DATES},
        )
        self.project.write("corpus/_schema.awawa", PROJECT_SCHEMA)
        self.project.write("corpus/tasks.awawa", MAIN_TASKS)
        self.project.track("corpus")
        self.project.run_git("commit", "--quiet", "-m", "the corpus")
        self.project.run_git("checkout", "--quiet", "-b", WAVE_BRANCH)
        self.project.write("corpus/tasks.awawa", WAVE_TASKS)
        self.project.write("corpus/milestones.awawa", WAVE_MILESTONES)
        self.project.write("corpus/questions.awawa", WAVE_QUESTIONS)
        self.project.track("corpus")
        self.project.run_git("commit", "--quiet", "-m", "the plan of M1")
        self.project.run_git("checkout", "--quiet", "main")
        self.machine.run_brigade(
            CLONE_ENTRY_POINT,
            "project",
            "add",
            str(self.project.path),
            *(argument for command in self.setup_commands for argument in ("--setup", command)),
        )
        (self.machine.corpus / "requests.awawa").write_text(RUNNING_REQUEST)
        (self.state / "ledger").mkdir(parents=True)
        (self.state / "ledger" / "2026-10.jsonl").write_text(QUEUED_S3)


class LaunchingTickTestCase(WaveTickTestCase, FileWaitingTestCase):
    def setUp(self):
        super().setUp()
        recordings = Path(self.root.name) / "recordings"
        recordings.mkdir()
        (recordings / "builder.json").write_text(json.dumps(DONE_RESULT))
        instructions = Path(self.root.name) / "instructions"
        (instructions / "procedures").mkdir(parents=True)
        (instructions / "procedures" / "build-task.md").write_text(BUILD_PROCEDURE)
        self.configure(recordings, instructions)
        self.worktree = self.project.path / ".brigade" / "worktrees" / "S3"

    def configure(self, recordings: Path, instructions: Path, keys: str = "") -> None:
        self.machine.write_configuration(
            f'client = "fake"\ndocument = "markdown"\ninstructions = "{instructions}"\n{keys}'
            f'[clients.fake]\nrecordings = "{recordings}"\n{COUNTING_CLIENT}'
        )

    def read_events(self, name: str) -> list:
        lines = "".join(path.read_text() for path in sorted((self.state / "ledger").glob("*.jsonl"))).splitlines()
        return [event for event in map(json.loads, lines) if event["event"] == name]

    def tearDown(self):
        for record in self.read_run_records():
            self.wait_for_file(self.state / "runs" / record["run"] / "result.json")
        super().tearDown()

    def read_run_records(self) -> list:
        return [json.loads(path.read_text()) for path in sorted((self.state / "runs").glob("*/run.json"))]


class BrigadeTickOnceLaunchingTheStartableTasksTest(LaunchingTickTestCase):
    def test_should_cut_the_worktree_of_each_startable_task_from_the_head_of_the_wave_branch(self):
        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            self.project.run_git("-C", str(self.worktree), "branch", "--show-current").strip(), TASK_BRANCH
        )
        self.assertEqual(
            self.project.run_git("rev-parse", f"{TASK_BRANCH}").strip(),
            self.project.run_git("rev-parse", WAVE_BRANCH).strip(),
        )

    def test_should_ignore_the_worktrees_on_the_wave_branch_once(self):
        # Act
        self.run_tick("--once")

        # Assert
        self.assertEqual(self.project.run_git("show", f"{WAVE_BRANCH}:.gitignore"), ".brigade/worktrees/\n")
        self.assertEqual(
            self.project.run_git("log", "--format=%s", f"main..{WAVE_BRANCH}").splitlines(),
            ["brigade tick: ignore .brigade/worktrees/", "the plan of M1"],
        )

    def test_should_run_the_setup_commands_of_the_project_in_the_worktree(self):
        # Act
        self.run_tick("--once")

        # Assert
        self.assertTrue((self.worktree / "setup-ran").is_file())

    def test_should_record_each_launched_task_running_in_the_wave(self):
        # Act
        self.run_tick("--once")

        # Assert
        self.assertEqual(
            self.read_events("task.state"),
            [
                {
                    "schema_version": 1,
                    "ts": "2026-10-13T10:00:00Z",
                    "event": "task.state",
                    "wave": "M1",
                    "task": "S3",
                    "state": "queued",
                },
                {"schema_version": 1, "ts": ANY, "event": "task.state", "wave": "M1", "task": "S3", "state": "running"},
                {"schema_version": 1, "ts": ANY, "event": "task.state", "wave": "M1", "task": "S6", "state": "running"},
            ],
        )

    def test_should_launch_the_build_procedure_detached_as_the_build_slot_of_the_project_in_the_worktree(self):
        # Act
        self.run_tick("--once")

        # Assert
        self.assertCountEqual(
            self.read_run_records(),
            [
                {
                    "schema_version": 1,
                    "run": ANY,
                    "procedure_path": ANY,
                    "role": "builder",
                    "role_source": ANY,
                    "client": "fake",
                    "worktree": str(self.worktree),
                    "capabilities": ["read", "write", "shell"],
                    "budget": 75,
                    "wall_limit_s": ANY,
                    "procedure": "build-task",
                    "slot": "build",
                    "project": "shop",
                    "cwd": str(self.worktree),
                    "arguments": {"task": "@TASK.S3", "base": WAVE_BRANCH},
                },
                {
                    "schema_version": 1,
                    "run": ANY,
                    "procedure_path": ANY,
                    "role": "builder",
                    "role_source": ANY,
                    "client": "fake",
                    "worktree": str(self.worktree.parent / "S6"),
                    "capabilities": ["read", "write", "shell"],
                    "budget": 75,
                    "wall_limit_s": ANY,
                    "procedure": "build-task",
                    "slot": "build",
                    "project": "shop",
                    "cwd": str(self.worktree.parent / "S6"),
                    "arguments": {"task": "@TASK.S6", "base": WAVE_BRANCH},
                },
            ],
        )

    def test_should_brief_the_build_run_with_the_project_the_wave_the_task_its_base_and_its_worktree(self):
        # Act
        self.run_tick("--once")

        # Assert
        self.assertEqual(
            (self.state / "briefs" / "shop_1-S3.md").read_text(),
            "Deliver @TASK.S3 of @PROJECT.shop, in the wave @MILESTONE.M1 of @REQUEST.shop_1.\n"
            "\n"
            f"- Base branch: {WAVE_BRANCH}.\n"
            f"- Worktree: {self.worktree}, on the branch {TASK_BRANCH}, cut from the head of {WAVE_BRANCH}.\n",
        )

    def test_should_take_the_lock_of_the_worktrees_of_the_project(self):
        # Act
        self.run_tick("--once")

        # Assert
        self.assertTrue((self.state / "locks" / "worktrees-shop.lock").is_file())

    def test_should_launch_nothing_more_at_the_next_tick(self):
        # Arrange
        self.run_tick("--once")

        # Act
        completed = self.run_tick("--once", "--json")

        # Assert
        self.assertEqual(json.loads(completed.stdout)["actions_applied"], 0)


class BrigadeTickOnceWithAFailingSetupTest(LaunchingTickTestCase):
    setup_commands = ("false",)

    def test_should_remove_the_worktree_and_its_branch_and_report_the_failure(self):
        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertIn("the setup of @TASK.S3 failed", completed.stderr)
        self.assertFalse(self.worktree.exists())
        self.assertEqual(self.project.run_git("branch", "--list", TASK_BRANCH), "")

    def test_should_record_the_task_parked_in_the_wave(self):
        # Act
        self.run_tick("--once")

        # Assert
        self.assertEqual(
            self.read_events("task.state"),
            [
                {
                    "schema_version": 1,
                    "ts": "2026-10-13T10:00:00Z",
                    "event": "task.state",
                    "wave": "M1",
                    "task": "S3",
                    "state": "queued",
                },
                {"schema_version": 1, "ts": ANY, "event": "task.state", "wave": "M1", "task": "S3", "state": "parked"},
            ],
        )

    def test_should_not_prepare_the_parked_task_again_at_the_next_tick(self):
        # Arrange
        self.run_tick("--once")

        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertNotIn("the setup of @TASK.S3 failed", completed.stderr)


class BrigadeTickOnceWithASetupLeavingTheWaveBranchTest(LaunchingTickTestCase):
    setup_commands = ("git checkout --quiet --orphan elsewhere", "git commit --quiet --allow-empty -m elsewhere")

    def test_should_remove_the_worktree_whose_head_no_longer_descends_from_the_wave_branch(self):
        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertIn("the setup of @TASK.S3 failed", completed.stderr)
        self.assertFalse(self.worktree.exists())


class BrigadeTickOnceWithASetupLineOfShellSyntaxTest(LaunchingTickTestCase):
    setup_commands = ('touch "$PWD"',)

    def test_should_run_the_line_as_one_argv_without_a_shell(self):
        # Act
        self.run_tick("--once")

        # Assert
        self.assertTrue((self.worktree / "$PWD").is_file())


class BrigadeTickOnceWithASetupFailingOnItsFirstLineTest(LaunchingTickTestCase):
    setup_commands = ("false", "touch ../../../second-line-ran")

    def test_should_run_no_line_after_the_failing_one(self):
        # Act
        self.run_tick("--once")

        # Assert
        self.assertFalse((self.project.path / "second-line-ran").exists())


class BrigadeTickOnceWithASetupLineThatSplitsIntoNoArgvTest(LaunchingTickTestCase):
    setup_commands = ("touch ../../../first-line-ran", 'touch "unclosed')

    def test_should_remove_the_worktree_and_its_branch_and_name_the_line(self):
        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertIn(
            'brigade tick: the setup of @TASK.S3 failed: the line touch "unclosed splits into no argv', completed.stderr
        )
        self.assertFalse(self.worktree.exists())
        self.assertEqual(self.project.run_git("branch", "--list", TASK_BRANCH), "")

    def test_should_run_no_line_of_the_setup(self):
        # Act
        self.run_tick("--once")

        # Assert
        self.assertFalse((self.project.path / "first-line-ran").exists())


class BrigadeTickOnceWithTheWaveBranchCheckedOutTest(LaunchingTickTestCase):
    def setUp(self):
        super().setUp()
        self.project.run_git("checkout", "--quiet", WAVE_BRANCH)

    def test_should_refuse_to_move_the_checked_out_wave_branch(self):
        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(completed.returncode, 1)
        self.assertIn(
            f"brigade tick: the wave branch {WAVE_BRANCH} is checked out in {self.project.path}", completed.stderr
        )

    def test_should_leave_the_checkout_and_its_branch_as_they_were(self):
        # Arrange
        head = self.project.run_git("rev-parse", WAVE_BRANCH)

        # Act
        self.run_tick("--once")

        # Assert
        self.assertEqual(self.project.run_git("status", "--porcelain"), "")
        self.assertEqual(self.project.run_git("rev-parse", WAVE_BRANCH), head)


class BrigadeTickOnceUnderAConfiguredWorktreeRootTest(LaunchingTickTestCase):
    def test_should_cut_the_worktree_under_the_root_relative_to_the_repository_and_leave_the_gitignore_alone(self):
        # Arrange
        recordings = Path(self.root.name) / "recordings"
        instructions = Path(self.root.name) / "instructions"
        self.configure(recordings, instructions, keys='worktree_root = "../worktrees"\n')

        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue((self.project.path.parent / "worktrees" / "S3").is_dir())
        self.assertEqual(self.project.run_git("ls-tree", "--name-only", WAVE_BRANCH), "corpus\n")


class BrigadeTickDryRunOnARunningWaveTest(WaveTickTestCase):
    def test_should_print_the_wave_its_tasks_their_states_and_the_project_with_the_tasks_to_launch(self):
        # Act
        completed = self.run_tick("--dry-run", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        document = json.loads(completed.stdout)
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "mode": "dry-run",
                "snapshot": {
                    "schema_version": 1,
                    "now": ANY,
                    "waves": [
                        {
                            "request": "shop_1",
                            "project": "shop",
                            "milestone": "M1",
                            "branch": WAVE_BRANCH,
                            "tasks": [
                                {"task": "S3", "after": ["S2"], "blocked_by": []},
                                {"task": "S4", "after": ["S3"], "blocked_by": []},
                                {"task": "S5", "after": [], "blocked_by": ["OPEN_QUESTION.Undecided"]},
                                {"task": "S6", "after": [], "blocked_by": []},
                            ],
                            "states": {"S3": "queued"},
                            "implemented": ["S2"],
                        }
                    ],
                    "projects": [{"project": "shop", "slots": 4, "live_runs": []}],
                    "planned": [],
                    "studies": [],
                    "live_study_runs": [],
                    "study_runs": 2,
                },
                "plan": [
                    {"request": "shop_1", "project": "shop", "milestone": "M1", "branch": WAVE_BRANCH, "task": "S3"},
                    {"request": "shop_1", "project": "shop", "milestone": "M1", "branch": WAVE_BRANCH, "task": "S6"},
                ],
            },
        )


class BrigadeTickOnceOnAPlannedRequestTest(LaunchingTickTestCase):
    def test_should_start_the_planned_request_under_the_automatic_plan_review_of_the_project(self):
        # Arrange
        (self.machine.corpus / "requests.awawa").write_text(PLANNED_WAVE_REQUEST)

        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            self.read_events("wave.started"),
            [{"schema_version": 1, "ts": ANY, "event": "wave.started", "wave": "M1", "project": "shop"}],
        )


class BrigadeTickDryRunWhileBuildRunsAreLiveTest(LaunchingTickTestCase):
    def tearDown(self):
        for record in self.read_run_records():
            self.wait_for_file(self.state / "runs" / record["run"] / "pid")
            self.machine.run_brigade(CLONE_ENTRY_POINT, "runs", "stop", record["run"])
        super().tearDown()

    def configure_client_outliving_the_test(self) -> None:
        recordings = Path(self.root.name) / "recordings"
        instructions = Path(self.root.name) / "instructions"
        self.machine.write_configuration(
            f'client = "fake"\ndocument = "markdown"\ninstructions = "{instructions}"\n'
            f'[clients.fake]\nrecordings = "{recordings}"\n{COUNTING_CLIENT}{CLIENT_OUTLIVING_THE_TEST}'
        )

    def test_should_count_the_live_build_runs_of_the_project(self):
        # Arrange
        self.configure_client_outliving_the_test()
        self.run_tick("--once")

        # Act
        completed = self.run_tick("--dry-run", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout)["snapshot"]["projects"],
            [
                {
                    "project": "shop",
                    "slots": 4,
                    "live_runs": [{"run": ANY, "slot": "build"}, {"run": ANY, "slot": "build"}],
                }
            ],
        )

    def test_should_leave_out_the_finished_runs_and_the_runs_of_no_project(self):
        # Arrange
        self.machine.run_brigade(
            CLONE_ENTRY_POINT,
            "run",
            "build-task",
            "--slot",
            "build",
            "--project",
            "shop",
            "--cwd",
            str(self.project.path),
        )
        self.configure_client_outliving_the_test()
        self.machine.run_brigade(
            CLONE_ENTRY_POINT, "run", "build-task", "--slot", "build", "--cwd", str(self.project.path), "--detach"
        )

        # Act
        completed = self.run_tick("--dry-run", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout)["snapshot"]["projects"], [{"project": "shop", "slots": 4, "live_runs": []}]
        )


ASKING_POLICY = "POLICY shop_review\n\tPROJECT @PROJECT.shop\n\tPLAN_REVIEW ask\n"


class BrigadeTickDryRunOfTheProjectsAndThePlannedRequestsTest(WaveTickTestCase):
    def test_should_read_the_slots_of_the_project(self):
        # Arrange
        (self.machine.corpus / "projects.awawa").write_text(
            f'PROJECT shop\n\tPATH "{self.project.path}"\n\tMAIN "main"\n\tSLOTS 1\n\tSTATUS active\n'
        )

        # Act
        completed = self.run_tick("--dry-run", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout)["snapshot"]["projects"], [{"project": "shop", "slots": 1, "live_runs": []}]
        )

    def test_should_hold_each_planned_request_with_the_plan_review_of_its_project(self):
        for case, policies, expected in [
            ("no policy", "", [{"request": "shop_2", "project": "shop", "plan_review": "auto"}]),
            ("a policy asking", ASKING_POLICY, [{"request": "shop_2", "project": "shop", "plan_review": "ask"}]),
        ]:
            with self.subTest(case=case):
                # Arrange
                (self.machine.corpus / "policies.awawa").write_text(policies)
                (self.machine.corpus / "requests.awawa").write_text(RUNNING_REQUEST + "\n" + PLANNED_REQUEST)

                # Act
                completed = self.run_tick("--dry-run", "--json")

                # Assert
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(json.loads(completed.stdout)["snapshot"]["planned"], expected)


class BrigadeTickDryRunTest(TickTestCase):
    def test_should_print_the_snapshot_and_the_empty_plan_in_the_versioned_document(self):
        # Act
        completed = self.run_tick("--dry-run", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        document = json.loads(completed.stdout)
        self.assertRegex(document["snapshot"]["now"], INSTANT)
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "mode": "dry-run",
                "snapshot": {
                    "schema_version": 1,
                    "now": document["snapshot"]["now"],
                    "waves": [],
                    "projects": [],
                    "planned": [],
                    "studies": [],
                    "live_study_runs": [],
                    "study_runs": 2,
                },
                "plan": [],
            },
        )

    def test_should_take_no_lock_and_write_no_heartbeat(self):
        # Act
        completed = self.run_tick("--dry-run")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertFalse(self.state.exists())

    def test_should_plan_while_another_tick_holds_the_lock(self):
        # Arrange
        self.hold_tick_lock()

        # Act
        completed = self.run_tick("--dry-run", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["plan"], [])

    def test_should_print_the_snapshot_and_the_plan_as_text(self):
        # Act
        completed = self.run_tick("--dry-run")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report_lines = completed.stdout.splitlines()
        self.assertRegex(report_lines[1], r"^  now  \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        self.assertEqual(
            report_lines,
            [
                "snapshot",
                report_lines[1],
                "  waves  []",
                "  projects  []",
                "  planned  []",
                "  studies  []",
                "  live_study_runs  []",
                "  study_runs  2",
                "plan",
                "  no action",
            ],
        )


class BrigadeTickLoopTest(TickTestCase):
    def test_should_tick_at_once_and_exit_0_on_a_signal(self):
        # Arrange
        rows = [("SIGTERM", signal.SIGTERM), ("SIGINT", signal.SIGINT)]
        for name, stop_signal in rows:
            with self.subTest(signal=name):
                # Arrange
                loop = self.start_loop("--json")
                self.wait_for_first_tick(loop)

                # Act
                loop.send_signal(stop_signal)

                # Assert
                stdout, stderr = loop.communicate(timeout=STOP_WAIT_S)
                self.assertEqual(loop.returncode, 0, stderr)
                self.assertEqual(json.loads(stdout), {"schema_version": 1, "mode": "loop", "ticks_attempted": 1})

    def test_should_report_each_tick_on_stderr(self):
        # Arrange
        loop = self.start_loop("--json")
        first_report = self.wait_for_first_tick(loop)

        # Act
        loop.send_signal(signal.SIGTERM)

        # Assert
        _, later_reports = loop.communicate(timeout=STOP_WAIT_S)
        self.assertRegex(
            first_report, r"^brigade tick: \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z: 0 actions applied in \d+ ms\n$"
        )
        self.assertEqual(later_reports, "")

    def test_should_print_the_ticks_attempted_as_text(self):
        # Arrange
        loop = self.start_loop()
        self.wait_for_first_tick(loop)

        # Act
        loop.send_signal(signal.SIGTERM)

        # Assert
        stdout, stderr = loop.communicate(timeout=STOP_WAIT_S)
        self.assertEqual((loop.returncode, stdout), (0, "tick --loop: 1 ticks attempted\n"), stderr)

    def test_should_write_the_trail_of_its_first_round(self):
        # Arrange
        loop = self.start_loop()
        self.wait_for_first_tick(loop)

        # Act
        loop.send_signal(signal.SIGTERM)

        # Assert
        loop.communicate(timeout=STOP_WAIT_S)
        [trail] = (self.state / "ticks").iterdir()
        self.assertRegex(trail.name, r"^\d{8}T\d{6}Z\.jsonl$")


class BrigadeTickLoopWhileAnotherTickHoldsTheLockTest(TickTestCase):
    def test_should_stand_down_on_stderr_and_exit_0_on_a_signal(self):
        # Arrange
        self.hold_tick_lock()
        loop = self.start_loop("--json")
        stand_down_line = self.wait_for_first_tick(loop)

        # Act
        loop.send_signal(signal.SIGTERM)

        # Assert
        stdout, _ = loop.communicate(timeout=STOP_WAIT_S)
        self.assertEqual(
            (stand_down_line, loop.returncode, json.loads(stdout)),
            (
                f"brigade tick: another tick holds {self.lock}\n",
                0,
                {"schema_version": 1, "mode": "loop", "ticks_attempted": 1},
            ),
        )
        self.assertFalse(self.heartbeat.exists())


class BrigadeTickWithoutAModeTest(TickTestCase):
    def test_should_refuse_with_its_usage(self):
        # Act
        completed = self.run_tick()

        # Assert
        self.assertEqual(completed.returncode, 2)
        self.assertIn("one of the arguments --once --dry-run --loop is required", completed.stderr)


@unittest.skipIf(os.geteuid() == 0, "root writes where the permissions refuse it")
class BrigadeTickOnceWhereTheMachineRefusesTheStateDirectoryTest(TickTestCase):
    def setUp(self):
        super().setUp()
        self.machine.state_home.mkdir()

    def tearDown(self):
        self.machine.state_home.chmod(0o700)
        super().tearDown()

    def test_should_exit_1_naming_the_state_directory_it_cannot_create(self):
        # Arrange
        self.machine.state_home.chmod(0o500)

        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout, completed.stderr),
            (1, "", f"brigade tick: cannot write {self.state}: Permission denied\n"),
        )


@unittest.skipIf(os.geteuid() == 0, "root writes where the permissions refuse it")
class BrigadeTickOnceWhereTheMachineRefusesAWriteInTheStateDirectoryTest(TickTestCase):
    def setUp(self):
        super().setUp()
        self.lock.parent.mkdir(parents=True)

    def tearDown(self):
        self.state.chmod(0o700)
        super().tearDown()

    def test_should_exit_1_naming_the_lock_it_cannot_open(self):
        # Arrange
        self.lock.touch(mode=0o400)

        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout, completed.stderr),
            (1, "", f"brigade tick: cannot write {self.lock}: Permission denied\n"),
        )

    def test_should_exit_1_naming_the_trail_directory_it_cannot_create_and_write_no_heartbeat(self):
        # Arrange
        self.state.chmod(0o500)

        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(
            (
                completed.returncode,
                completed.stdout,
                completed.stderr,
                sorted(path.name for path in self.state.iterdir()),
            ),
            (1, "", f"brigade tick: cannot write {self.state / 'ticks'}: Permission denied\n", ["locks"]),
        )

    def test_should_exit_1_naming_the_heartbeat_it_cannot_write_and_write_none(self):
        # Arrange
        (self.state / "ticks").mkdir()
        self.state.chmod(0o500)

        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stdout, completed.stderr, self.heartbeat.exists()),
            (1, "", f"brigade tick: cannot write {self.heartbeat}: Permission denied\n", False),
        )


@unittest.skipIf(os.geteuid() == 0, "root writes where the permissions refuse it")
class BrigadeTickLoopWhereTheMachineRefusesTheWriteTest(TickTestCase):
    def setUp(self):
        super().setUp()
        self.machine.state_home.mkdir()
        self.machine.state_home.chmod(0o500)

    def tearDown(self):
        self.machine.state_home.chmod(0o700)
        super().tearDown()

    def test_should_report_the_failed_tick_and_keep_ticking_until_a_signal(self):
        # Arrange
        loop = self.start_loop("--json")
        failure_line = self.wait_for_first_tick(loop)

        # Act
        loop.send_signal(signal.SIGTERM)

        # Assert
        stdout, later_reports = loop.communicate(timeout=STOP_WAIT_S)
        self.assertEqual(
            (failure_line, later_reports, loop.returncode, self.state.exists()),
            (f"brigade tick: cannot write {self.state}: Permission denied\n", "", 0, False),
        )
        self.assertEqual(json.loads(stdout), {"schema_version": 1, "mode": "loop", "ticks_attempted": 1})


class BrigadeTickOnceKeepingTheSetupOfTheWorktreeTest(LaunchingTickTestCase):
    setup_commands = ("touch setup-ran", "git branch --show-current")

    def test_should_keep_each_setup_command_and_its_output_in_the_setup_log_of_the_task(self):
        # Act
        self.run_tick("--once")

        # Assert
        self.assertEqual(
            (self.state / "setups" / "shop" / "S3.log").read_text(),
            "$ touch setup-ran\n$ git branch --show-current\ntask/M1-empty-cart/S3\n",
        )


ORDER_END_EVENTS = ("order.done", "order.parked")
ORDER_WAIT_S = 30.0
ORDER_POLL_S = 0.1
CLIENT_LIVING_A_FEW_SECONDS = 'delay = "5"\n'
WEEKLY_RUN = "20261001T090000Z-a1b2c3"
WEEKLY_STARTED_LONG_AGO = (
    '{"schema_version": 1, "ts": "2026-10-01T09:00:00Z", "event": "order.started", "project": null,'
    f' "kind": "study", "order": "weekly", "run": "{WEEKLY_RUN}"}}\n'
)
WEEKLY_RECORD = {"schema_version": 1, "study": "weekly", "project": None}


class StudyTickTestCase(TickTestCase, FileWaitingTestCase):
    client_keys = ""
    configuration_keys = ""

    def setUp(self):
        super().setUp()
        provide_awawa(self)
        self.machine.run_init()
        recordings = Path(self.root.name) / "recordings"
        recordings.mkdir()
        (recordings / "reporter.json").write_text(json.dumps(DONE_RESULT))
        self.machine.write_configuration(
            f'client = "fake"\ndocument = "markdown"\n{self.configuration_keys}'
            f'[clients.fake]\nrecordings = "{recordings}"\n{COUNTING_CLIENT}{self.client_keys}'
        )

    def tearDown(self):
        for study in self.read_started_studies():
            self.wait_for_order_end(study)
        super().tearDown()

    def record_study(self, name: str, slot: str = "report") -> None:
        self.machine.run_brigade(
            CLONE_ENTRY_POINT,
            "study",
            "new",
            name,
            "--title",
            f"the {name} study",
            "--collector",
            "shell: true",
            "--slot",
            slot,
            "--every",
            "1h",
            "--output",
            "entity:ANSWER",
        )

    def read_events(self, name: str) -> list:
        lines = "".join(path.read_text() for path in sorted((self.state / "ledger").glob("*.jsonl"))).splitlines()
        return [event for event in map(json.loads, lines) if event["event"] == name]

    def read_started_studies(self) -> set:
        return {event["order"] for event in self.read_events("order.started")}

    def read_order_events(self, study: str) -> list:
        lines = "".join(path.read_text() for path in sorted((self.state / "ledger").glob("*.jsonl"))).splitlines()
        runs = {event["run"] for event in self.read_events("order.started") if event["order"] == study}
        return [
            (event["event"], event.get("step"))
            for event in map(json.loads, lines)
            if event["event"].startswith(("order.", "step.")) and event["run"] in runs
        ]

    def wait_for_order_end(self, study: str) -> None:
        deadline = time.monotonic() + ORDER_WAIT_S
        while not any(event in ORDER_END_EVENTS for event, _ in self.read_order_events(study)):
            if time.monotonic() > deadline:
                self.fail(f"the run of @STUDY.{study} never ended")
            time.sleep(ORDER_POLL_S)


class BrigadeTickOnceWithADueStudyTest(StudyTickTestCase):
    def test_should_run_the_due_study_through_study_run(self):
        # Arrange
        self.record_study("weekly")

        # Act
        self.run_tick("--once")

        # Assert
        self.wait_for_order_end("weekly")
        self.assertEqual(
            self.read_order_events("weekly"),
            [("order.started", None), ("step.done", "collect"), ("step.failed", "judge"), ("order.parked", "judge")],
        )

    def test_should_launch_no_study_started_within_its_schedule(self):
        # Arrange
        self.record_study("trees", slot="none")
        self.machine.run_brigade(CLONE_ENTRY_POINT, "study", "run", "trees")

        # Act
        completed = self.run_tick("--once", "--json")

        # Assert
        self.assertEqual(json.loads(completed.stdout)["actions_applied"], 0)

    def test_should_launch_no_paused_study(self):
        # Arrange
        self.record_study("weekly")
        self.machine.run_brigade(CLONE_ENTRY_POINT, "study", "pause", "weekly")

        # Act
        completed = self.run_tick("--once", "--json")

        # Assert
        self.assertEqual(json.loads(completed.stdout)["actions_applied"], 0)


class BrigadeTickOnceWithTheStudyRunsTakenTest(StudyTickTestCase):
    client_keys = CLIENT_LIVING_A_FEW_SECONDS
    configuration_keys = "study_runs = 1\n"

    def test_should_launch_no_more_judging_studies_than_the_study_runs(self):
        # Arrange
        self.record_study("monthly")
        self.record_study("weekly")

        # Act
        self.run_tick("--once")

        # Assert
        self.assertEqual(self.read_started_studies(), {"monthly"})

    def test_should_launch_a_scan_beyond_the_study_runs(self):
        # Arrange
        self.record_study("monthly")
        self.record_study("trees", slot="none")

        # Act
        self.run_tick("--once")

        # Assert
        self.assertEqual(self.read_started_studies(), {"monthly", "trees"})


class BrigadeTickOnceWhileARunOfTheStudyIsLiveTest(StudyTickTestCase):
    client_keys = CLIENT_LIVING_A_FEW_SECONDS

    def setUp(self):
        super().setUp()
        self.record_study("weekly")
        (self.state / "ledger").mkdir(parents=True, exist_ok=True)
        (self.state / "ledger" / "2026-10.jsonl").write_text(WEEKLY_STARTED_LONG_AGO)
        (self.state / "runs" / WEEKLY_RUN).mkdir(parents=True)
        (self.state / "runs" / WEEKLY_RUN / "study.json").write_text(json.dumps(WEEKLY_RECORD))
        self.live_run = ProcessLauncher.start(
            [sys.executable, str(CLONE_ENTRY_POINT), "study", "run", "weekly", "--run-id", WEEKLY_RUN],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=self.machine.describe_environment(),
        )
        self.wait_for_file(self.state / "runs" / WEEKLY_RUN / "pid")

    def tearDown(self):
        self.live_run.wait()
        super().tearDown()

    def test_should_launch_no_study_while_a_run_of_it_is_live(self):
        # Act
        completed = self.run_tick("--once", "--json")

        # Assert
        self.assertEqual(json.loads(completed.stdout)["actions_applied"], 0)
