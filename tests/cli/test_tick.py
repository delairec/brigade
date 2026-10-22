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
from tests.cli.temporary_machine import CLONE_ENTRY_POINT, REPOSITORY_ROOT, TemporaryMachine
from tests.cli.temporary_project import PINNED_COMMIT_DATES, TemporaryProject
from tests.cli.test_collect import install_executable
from tests.cli.test_verify_preflight import (
    PULL_REQUEST_BODY,
    PULL_REQUEST_TITLE,
    SUCCESSFUL_CHECK_RUN,
    VerifyPreflightTestCase,
)
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
WAVE_EVENTS = (
    '{"schema_version": 2, "ts": "2026-10-13T09:00:00Z", "event": "wave.started", "wave": "shop_w1",'
    f' "project": "shop", "branch": "{WAVE_BRANCH}", "tasks": ["S3", "S4", "S5", "S6"]}}\n'
    '{"schema_version": 1, "ts": "2026-10-13T10:00:00Z", "event": "task.state", "wave": "shop_w1", "task": "S3",'
    ' "state": "queued"}\n'
    '{"schema_version": 1, "ts": "2026-10-13T10:30:00Z", "event": "task.state", "wave": "cafe_w1", "task": "S6",'
    ' "state": "running"}\n'
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
        self.assertEqual(
            heartbeat, {"schema_version": 1, "ts": ANY, "duration_ms": ANY, "actions_applied": 0, "actions_failed": 0}
        )

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
                "actions_failed": 0,
                "heartbeat": str(self.heartbeat),
            },
        )

    def test_should_print_the_tick_as_text(self):
        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertRegex(
            completed.stdout, r"^tick \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z: 0 actions applied, 0 failed in \d+ ms\n$"
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


REPLACING_PROCEDURE = "---\ncapabilities: read, shell\nbudget: 40\n---\nDeliver the task another way.\n"
SHIPPED_BUILD_PROCEDURE = REPOSITORY_ROOT / "brigade" / "runs" / "data" / "procedures" / "build-task.md"
TASK_BRANCH = "task/M1-empty-cart/S3"
TOKENLESS_LOGIN = "octo-tokenless"
LOCK_WAIT_S = 5


FAKE_GH = (
    "#!/bin/sh\n"
    'printf \'%s %s\\n\' "${{GH_TOKEN:-no GH_TOKEN}}" "$*" >> "{calls}"\n'
    'case "$1 $2" in\n'
    '  "auth token") if [ "$6" = "{tokenless}" ]; then exit 1; fi; printf \'token-of-%s\\n\' "$6" ;;\n'
    '  "pr list") answer="{pull_requests}/$(printf \'%s\' "$4" | tr / -)"\n'
    '    if [ -f "$answer.refused" ]; then echo "HTTP 502: Bad Gateway" >&2; exit 1; fi\n'
    '    if [ -f "$answer.json" ]; then cat "$answer.json"; else echo "[]"; fi ;;\n'
    '  "api repos/{{owner}}/{{repo}}/compare/"*) if [ -f "{pull_requests}/behind-by" ]; then\n'
    '    cat "{pull_requests}/behind-by"; else echo 0; fi ;;\n'
    "  *) exit 2 ;;\n"
    "esac\n"
)
PULL_REQUEST_OF_S3 = (
    '[{{"number": 42, "state": "{state}", "headRefOid": "0123abc", "baseRefName": "integration/M1-empty-cart",'
    ' "reviewDecision": "REVIEW_REQUIRED", "statusCheckRollup": [{{"__typename": "CheckRun", "name": "tests",'
    ' "status": "COMPLETED", "conclusion": "SUCCESS"}}]}}]\n'
)


class WaveTickTestCase(TickTestCase):
    setup_commands = ("touch setup-ran",)

    def run_tick(self, *options: str):
        return self.machine.run_brigade(CLONE_ENTRY_POINT, "tick", *options, environment=self.describe_environment())

    def read_events(self, name: str) -> list:
        lines = "".join(path.read_text() for path in sorted((self.state / "ledger").glob("*.jsonl"))).splitlines()
        return [event for event in map(json.loads, lines) if event["event"] == name]

    def describe_environment(self) -> dict:
        return {
            **self.machine.describe_environment(),
            **PINNED_COMMIT_DATES,
            "PATH": f"{self.tools}{os.pathsep}{os.environ['PATH']}",
        }

    def setUp(self):
        super().setUp()
        root = Path(self.root.name).resolve()
        self.tools = root / "tools"
        self.gh_calls = root / "gh-calls"
        self.pull_requests = root / "pull-requests"
        self.pull_requests.mkdir()
        install_executable(
            self.tools / "gh",
            FAKE_GH.format(calls=self.gh_calls, pull_requests=self.pull_requests, tokenless=TOKENLESS_LOGIN),
        )
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
        (self.state / "ledger").mkdir(parents=True)
        (self.state / "ledger" / "2026-10.jsonl").write_text(WAVE_EVENTS)


class LaunchingTickTestCase(WaveTickTestCase, FileWaitingTestCase):
    def setUp(self):
        super().setUp()
        recordings = Path(self.root.name) / "recordings"
        recordings.mkdir()
        (recordings / "builder.json").write_text(json.dumps(DONE_RESULT))
        instructions = Path(self.root.name) / "instructions"
        (instructions / "procedures").mkdir(parents=True)
        (instructions / "procedures" / "deliver.md").write_text(REPLACING_PROCEDURE)
        self.configure(recordings, instructions)
        self.worktree = self.project.path / ".brigade" / "worktrees" / "S3"
        self.worktree_of_s6 = self.project.path / ".brigade" / "worktrees" / "S6"

    def configure(self, recordings: Path, instructions: Path, keys: str = "") -> None:
        self.machine.write_configuration(
            f'client = "fake"\ndocument = "markdown"\ninstructions = "{instructions}"\n{keys}'
            f'[clients.fake]\nrecordings = "{recordings}"\n{COUNTING_CLIENT}'
        )

    def tearDown(self):
        self.wait_for_the_runs()
        super().tearDown()

    def wait_for_the_runs(self) -> None:
        for record in self.read_run_records():
            self.wait_for_file(self.state / "runs" / record["run"] / "result.json")

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
                    "wave": "shop_w1",
                    "task": "S3",
                    "state": "queued",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-13T10:30:00Z",
                    "event": "task.state",
                    "wave": "cafe_w1",
                    "task": "S6",
                    "state": "running",
                },
                {
                    "schema_version": 1,
                    "ts": ANY,
                    "event": "task.state",
                    "wave": "shop_w1",
                    "task": "S3",
                    "state": "running",
                },
                {
                    "schema_version": 1,
                    "ts": ANY,
                    "event": "task.state",
                    "wave": "shop_w1",
                    "task": "S6",
                    "state": "running",
                },
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
                    "procedure_path": str(SHIPPED_BUILD_PROCEDURE),
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
                    "wave": "shop_w1",
                    "task": "S3",
                    "brief": str(self.state / "briefs" / "shop_w1-S3.md"),
                },
                {
                    "schema_version": 1,
                    "run": ANY,
                    "procedure_path": str(SHIPPED_BUILD_PROCEDURE),
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
                    "wave": "shop_w1",
                    "task": "S6",
                    "brief": str(self.state / "briefs" / "shop_w1-S6.md"),
                },
            ],
        )

    def test_should_carry_the_wave_and_the_task_in_every_finished_build_run(self):
        # Act
        self.run_tick("--once")

        # Assert
        self.wait_for_the_runs()
        [first, second] = self.read_events("run.finished")
        self.assertCountEqual(
            [(first["wave"], first["task"]), (second["wave"], second["task"])], [("shop_w1", "S3"), ("shop_w1", "S6")]
        )

    def test_should_brief_the_build_run_with_the_project_the_wave_the_task_its_base_and_its_worktree(self):
        # Act
        self.run_tick("--once")

        # Assert
        self.assertEqual(
            (self.state / "briefs" / "shop_w1-S3.md").read_text(),
            "Deliver @TASK.S3 of @PROJECT.shop, in the wave shop_w1.\n"
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

    def test_should_leave_the_worktree_and_its_branch_and_record_the_failed_action(self):
        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            self.read_events("tick.action_failed")[0]["error"], "the setup of @TASK.S3 failed: false exited 1: "
        )
        self.assertTrue(self.worktree.is_dir())
        self.assertEqual(
            self.project.run_git("branch", "--list", "--format=%(refname:short)", TASK_BRANCH), f"{TASK_BRANCH}\n"
        )

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
                    "wave": "shop_w1",
                    "task": "S3",
                    "state": "queued",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-13T10:30:00Z",
                    "event": "task.state",
                    "wave": "cafe_w1",
                    "task": "S6",
                    "state": "running",
                },
                {
                    "schema_version": 1,
                    "ts": ANY,
                    "event": "task.state",
                    "wave": "shop_w1",
                    "task": "S3",
                    "state": "parked",
                    "reason": "setup failed",
                },
                {
                    "schema_version": 1,
                    "ts": ANY,
                    "event": "task.state",
                    "wave": "shop_w1",
                    "task": "S6",
                    "state": "parked",
                    "reason": "setup failed",
                },
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

    def test_should_park_the_task_whose_head_no_longer_descends_from_the_wave_branch_leaving_its_worktree(self):
        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("the setup of @TASK.S3 failed", self.read_events("tick.action_failed")[0]["error"])
        self.assertTrue(self.worktree.is_dir())


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

    def test_should_leave_the_worktree_and_its_branch_and_name_the_line(self):
        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            self.read_events("tick.action_failed")[0]["error"],
            'the setup of @TASK.S3 failed: the line touch "unclosed splits into no argv: No closing quotation',
        )
        self.assertTrue(self.worktree.is_dir())
        self.assertEqual(
            self.project.run_git("branch", "--list", "--format=%(refname:short)", TASK_BRANCH), f"{TASK_BRANCH}\n"
        )

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
        self.run_tick("--once")

        # Assert
        self.assertIn(
            f"the wave branch {WAVE_BRANCH} is checked out in {self.project.path}",
            self.read_events("tick.action_failed")[0]["error"],
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


class BrigadeTickOnceWithTheBuildProcedureReplacedTest(LaunchingTickTestCase):
    def test_should_launch_the_procedure_the_key_build_of_procedures_names_in_place_of_build_task(self):
        # Arrange
        recordings = Path(self.root.name) / "recordings"
        instructions = Path(self.root.name) / "instructions"
        self.configure(recordings, instructions, keys='[procedures]\nbuild = "deliver"\n')

        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertCountEqual(
            self.read_run_records(),
            [
                {
                    "schema_version": 1,
                    "run": ANY,
                    "procedure_path": str(instructions / "procedures" / "deliver.md"),
                    "role": "builder",
                    "role_source": ANY,
                    "client": "fake",
                    "worktree": str(self.worktree),
                    "capabilities": ["read", "shell"],
                    "budget": 40,
                    "wall_limit_s": ANY,
                    "procedure": "deliver",
                    "slot": "build",
                    "project": "shop",
                    "cwd": str(self.worktree),
                    "arguments": {"task": "@TASK.S3", "base": WAVE_BRANCH},
                    "wave": "shop_w1",
                    "task": "S3",
                    "brief": str(self.state / "briefs" / "shop_w1-S3.md"),
                },
                {
                    "schema_version": 1,
                    "run": ANY,
                    "procedure_path": str(instructions / "procedures" / "deliver.md"),
                    "role": "builder",
                    "role_source": ANY,
                    "client": "fake",
                    "worktree": str(self.worktree.parent / "S6"),
                    "capabilities": ["read", "shell"],
                    "budget": 40,
                    "wall_limit_s": ANY,
                    "procedure": "deliver",
                    "slot": "build",
                    "project": "shop",
                    "cwd": str(self.worktree.parent / "S6"),
                    "arguments": {"task": "@TASK.S6", "base": WAVE_BRANCH},
                    "wave": "shop_w1",
                    "task": "S6",
                    "brief": str(self.state / "briefs" / "shop_w1-S6.md"),
                },
            ],
        )


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
                            "project": "shop",
                            "wave": "shop_w1",
                            "branch": WAVE_BRANCH,
                            "tasks": [
                                {
                                    "task": "S3",
                                    "after": ["S2"],
                                    "blocked_by": [],
                                    "pull_request": None,
                                    "worktree": None,
                                    "rate_limit": None,
                                    "stopped_run": None,
                                    "opened_pull_request": None,
                                    "preflighted_head": None,
                                    "verdict": None,
                                    "reviewed_head": None,
                                    "preflight_failures": [],
                                    "repair_rounds": 0,
                                    "holds_uncommitted_changes": False,
                                },
                                {
                                    "task": "S4",
                                    "after": ["S3"],
                                    "blocked_by": [],
                                    "pull_request": None,
                                    "worktree": None,
                                    "rate_limit": None,
                                    "stopped_run": None,
                                    "opened_pull_request": None,
                                    "preflighted_head": None,
                                    "verdict": None,
                                    "reviewed_head": None,
                                    "preflight_failures": [],
                                    "repair_rounds": 0,
                                    "holds_uncommitted_changes": False,
                                },
                                {
                                    "task": "S5",
                                    "after": [],
                                    "blocked_by": ["OPEN_QUESTION.Undecided"],
                                    "pull_request": None,
                                    "worktree": None,
                                    "rate_limit": None,
                                    "stopped_run": None,
                                    "opened_pull_request": None,
                                    "preflighted_head": None,
                                    "verdict": None,
                                    "reviewed_head": None,
                                    "preflight_failures": [],
                                    "repair_rounds": 0,
                                    "holds_uncommitted_changes": False,
                                },
                                {
                                    "task": "S6",
                                    "after": [],
                                    "blocked_by": [],
                                    "pull_request": None,
                                    "worktree": None,
                                    "rate_limit": None,
                                    "stopped_run": None,
                                    "opened_pull_request": None,
                                    "preflighted_head": None,
                                    "verdict": None,
                                    "reviewed_head": None,
                                    "preflight_failures": [],
                                    "repair_rounds": 0,
                                    "holds_uncommitted_changes": False,
                                },
                            ],
                            "states": {"S3": "queued"},
                            "implemented": ["S2"],
                            "pause": None,
                            "forge_account_unavailable": False,
                            "branch_missing": False,
                            "reported": False,
                            "integration_pull_request": None,
                            "opened_integration_pull_request": None,
                        }
                    ],
                    "projects": [
                        {
                            "project": "shop",
                            "slots": 4,
                            "live_runs": [],
                            "wave_start": "auto",
                            "candidates": [],
                            "merge": "rebase",
                            "review": "verdict",
                            "auto_merge": "integration",
                            "verify_rounds": 2,
                            "awaits_check_runs": True,
                            "on_github": False,
                        }
                    ],
                    "studies": [],
                    "live_study_runs": [],
                    "study_runs": 2,
                    "rate_limits": [],
                },
                "plan": [
                    {
                        "wave": "shop_w1",
                        "task": "S5",
                        "reason": "blocked",
                        "blockers": ["OPEN_QUESTION.Undecided"],
                    },
                    {
                        "project": "shop",
                        "wave": "shop_w1",
                        "branch": WAVE_BRANCH,
                        "task": "S3",
                    },
                    {
                        "project": "shop",
                        "wave": "shop_w1",
                        "branch": WAVE_BRANCH,
                        "task": "S6",
                    },
                ],
            },
        )

    def test_should_read_no_pull_request_of_a_queued_task(self):
        # Act
        completed = self.run_tick("--dry-run", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertFalse(self.gh_calls.exists())


class LiveBuildRunTickTestCase(LaunchingTickTestCase):
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


class BrigadeTickDryRunWhileBuildRunsAreLiveTest(LiveBuildRunTickTestCase):
    def test_should_count_the_live_build_runs_of_the_project(self):
        # Arrange
        self.configure_client_outliving_the_test()
        self.run_tick("--once")

        # Act
        completed = self.run_tick("--dry-run", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertCountEqual(
            json.loads(completed.stdout)["snapshot"]["projects"][0]["live_runs"],
            [
                {"run": ANY, "slot": "build", "worktree": str(self.worktree)},
                {"run": ANY, "slot": "build", "worktree": str(self.worktree_of_s6)},
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
            json.loads(completed.stdout)["snapshot"]["projects"],
            [
                {
                    "project": "shop",
                    "slots": 4,
                    "live_runs": [],
                    "wave_start": "auto",
                    "candidates": [],
                    "merge": "rebase",
                    "review": "verdict",
                    "auto_merge": "integration",
                    "verify_rounds": 2,
                    "awaits_check_runs": True,
                    "on_github": False,
                }
            ],
        )


class BrigadeTickDryRunOfTheProjectsTest(WaveTickTestCase):
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
            json.loads(completed.stdout)["snapshot"]["projects"],
            [
                {
                    "project": "shop",
                    "slots": 1,
                    "live_runs": [],
                    "wave_start": "auto",
                    "candidates": [],
                    "merge": "rebase",
                    "review": "verdict",
                    "auto_merge": "integration",
                    "verify_rounds": 2,
                    "awaits_check_runs": True,
                    "on_github": False,
                }
            ],
        )


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
                    "studies": [],
                    "live_study_runs": [],
                    "study_runs": 2,
                    "rate_limits": [],
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
                "  studies  []",
                "  live_study_runs  []",
                "  study_runs  2",
                "  rate_limits  []",
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
            first_report,
            r"^brigade tick: \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z: 0 actions applied, 0 failed in \d+ ms\n$",
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
WEEKLY_RUN = "20261001T090000Z-a1b2c3"
WEEKLY_STARTED_LONG_AGO = (
    '{"schema_version": 1, "ts": "2026-10-01T09:00:00Z", "event": "order.started", "project": null,'
    f' "kind": "study", "order": "weekly", "run": "{WEEKLY_RUN}"}}\n'
)
WEEKLY_PARKED_LONG_AGO = WEEKLY_STARTED_LONG_AGO + (
    '{"schema_version": 1, "ts": "2026-10-01T09:05:00Z", "event": "order.parked", "project": null,'
    f' "kind": "study", "order": "weekly", "run": "{WEEKLY_RUN}", "step": "judge", "reason": "no answer"}}\n'
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
        self.gate.touch()
        for study in self.read_started_studies():
            self.wait_for_order_end(study)
        super().tearDown()

    @property
    def gate(self) -> Path:
        return Path(self.root.name) / "gate"

    @property
    def gated_collector(self) -> str:
        return f'shell: sh -c "until [ -e {self.gate} ]; do sleep 0.1; done"'

    def run_tick_before_the_collectors_end(self, *arguments: str) -> subprocess.CompletedProcess:
        try:
            return self.run_tick("--once", *arguments)
        finally:
            self.gate.touch()

    def record_study(self, name: str, slot: str = "report", collector: str = "shell: true") -> None:
        self.machine.run_brigade(
            CLONE_ENTRY_POINT,
            "study",
            "new",
            name,
            "--title",
            f"the {name} study",
            "--collector",
            collector,
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

    def test_should_launch_no_study_whose_last_run_parked(self):
        # Arrange
        self.record_study("weekly")
        (self.state / "ledger").mkdir(parents=True, exist_ok=True)
        (self.state / "ledger" / "2026-10.jsonl").write_text(WEEKLY_PARKED_LONG_AGO)

        # Act
        completed = self.run_tick("--once", "--json")

        # Assert
        self.assertEqual(json.loads(completed.stdout)["actions_applied"], 0)


class BrigadeTickOnceWithTheStudyRunsTakenTest(StudyTickTestCase):
    configuration_keys = "study_runs = 1\n"

    def test_should_launch_no_more_judging_studies_than_the_study_runs(self):
        # Arrange
        self.record_study("monthly", collector=self.gated_collector)
        self.record_study("weekly", collector=self.gated_collector)

        # Act
        self.run_tick_before_the_collectors_end()

        # Assert
        self.assertEqual(self.read_started_studies(), {"monthly"})

    def test_should_launch_a_scan_beyond_the_study_runs(self):
        # Arrange
        self.record_study("monthly", collector=self.gated_collector)
        self.record_study("trees", slot="none", collector=self.gated_collector)

        # Act
        self.run_tick_before_the_collectors_end()

        # Assert
        self.assertEqual(self.read_started_studies(), {"monthly", "trees"})


class LiveStudyRunTestCase(StudyTickTestCase):
    def setUp(self):
        super().setUp()
        self.record_study("weekly", collector=self.gated_collector)
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
        self.gate.touch()
        self.live_run.wait()
        super().tearDown()


class BrigadeTickOnceWhileARunOfTheStudyIsLiveTest(LiveStudyRunTestCase):
    def test_should_launch_no_study_while_a_run_of_it_is_live(self):
        # Act
        completed = self.run_tick_before_the_collectors_end("--json")

        # Assert
        self.assertEqual(json.loads(completed.stdout)["actions_applied"], 0)


RUNNING_S3 = (
    '{"schema_version": 1, "ts": "2026-10-13T11:00:00Z", "event": "task.state", "wave": "shop_w1", "task": "S3",'
    ' "state": "running"}\n'
)
CLI_KEYS = '[forge_accounts]\ncli = "octo-cli"\n'
TOKENLESS_CLI_KEYS = f'forge_attempts = 1\n[forge_accounts]\ncli = "{TOKENLESS_LOGIN}"\n'
MERGED_S3 = (
    '{"schema_version": 1, "ts": "2026-10-13T12:00:00Z", "event": "task.state", "wave": "shop_w1", "task": "S3",'
    ' "state": "merged"}\n'
)
CAFE_BRANCH = "integration/M1-menu"
CAFE_TASKS = 'TASK S6\n\tTITLE "Print the menu"\n\tSTATUS todo\n\tMILESTONE @MILESTONE.M1\n'
CAFE_MILESTONES = 'MILESTONE M1\n\tTITLE "Menu"\n\tSTATUS running\n'
CAFE_WAVE_STARTED = (
    '{"schema_version": 2, "ts": "2026-10-13T09:30:00Z", "event": "wave.started", "wave": "cafe_w1",'
    f' "project": "cafe", "branch": "{CAFE_BRANCH}", "tasks": ["S6"]}}\n'
)


class FollowingTickTestCase(LiveBuildRunTickTestCase):
    def setUp(self):
        super().setUp()
        with (self.state / "ledger" / "2026-10.jsonl").open("a") as ledger:
            ledger.write(RUNNING_S3)
        self.project.run_git("worktree", "add", "--quiet", "-b", TASK_BRANCH, str(self.worktree), WAVE_BRANCH)

    def answer_pull_request_of_s3(self, state: str) -> None:
        (self.pull_requests / "task-M1-empty-cart-S3.json").write_text(PULL_REQUEST_OF_S3.format(state=state))


class BrigadeTickDryRunFollowingThePullRequestOfARunningTaskTest(FollowingTickTestCase):
    def test_should_carry_the_pull_request_of_the_task_and_its_worktree(self):
        # Arrange
        self.answer_pull_request_of_s3("OPEN")

        # Act
        completed = self.run_tick("--dry-run", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout)["snapshot"]["waves"][0]["tasks"][0],
            {
                "task": "S3",
                "after": ["S2"],
                "blocked_by": [],
                "pull_request": {
                    "number": 42,
                    "state": "open",
                    "checks": [{"name": "tests", "verdict": "success"}],
                    "review": "review_required",
                    "behind": False,
                    "head": "0123abc",
                    "base": "integration/M1-empty-cart",
                },
                "worktree": str(self.worktree),
                "rate_limit": None,
                "stopped_run": None,
                "opened_pull_request": None,
                "preflighted_head": None,
                "verdict": None,
                "reviewed_head": None,
                "preflight_failures": [],
                "repair_rounds": 0,
                "holds_uncommitted_changes": False,
            },
        )

    def test_should_read_the_pull_request_as_the_login_of_the_key_cli(self):
        # Arrange
        self.configure(Path(self.root.name) / "recordings", Path(self.root.name) / "instructions", CLI_KEYS)
        self.answer_pull_request_of_s3("OPEN")

        # Act
        completed = self.run_tick("--dry-run", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn(
            "token-of-octo-cli pr list --head task/M1-empty-cart/S3 --state all --limit 1"
            " --json number,state,headRefOid,baseRefName,reviewDecision,statusCheckRollup",
            self.gh_calls.read_text().splitlines(),
        )

    def test_should_carry_that_the_base_of_the_pull_request_moved_past_its_head(self):
        # Arrange
        self.answer_pull_request_of_s3("OPEN")
        (self.pull_requests / "behind-by").write_text("3\n")

        # Act
        completed = self.run_tick("--dry-run", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout)["snapshot"]["waves"][0]["tasks"][0]["pull_request"],
            {
                "number": 42,
                "state": "open",
                "checks": [{"name": "tests", "verdict": "success"}],
                "review": "review_required",
                "behind": True,
                "head": "0123abc",
                "base": "integration/M1-empty-cart",
            },
        )

    def test_should_stop_on_the_login_of_the_key_cli_without_a_token(self):
        # Arrange
        self.configure(Path(self.root.name) / "recordings", Path(self.root.name) / "instructions", TOKENLESS_CLI_KEYS)
        self.answer_pull_request_of_s3("OPEN")

        # Act
        completed = self.run_tick("--dry-run", "--json")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stderr),
            (1, f"brigade tick: gh printed no token for the login {TOKENLESS_LOGIN}, bound to cli, after 1 attempt\n"),
        )


class BrigadeTickOnceFollowingThePullRequestOfARunningTaskTest(FollowingTickTestCase):
    def test_should_record_the_task_with_its_pull_request_open(self):
        # Arrange
        self.answer_pull_request_of_s3("OPEN")

        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            self.read_events("task.state"),
            [
                {
                    "schema_version": 1,
                    "ts": "2026-10-13T10:00:00Z",
                    "event": "task.state",
                    "wave": "shop_w1",
                    "task": "S3",
                    "state": "queued",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-13T10:30:00Z",
                    "event": "task.state",
                    "wave": "cafe_w1",
                    "task": "S6",
                    "state": "running",
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-13T11:00:00Z",
                    "event": "task.state",
                    "wave": "shop_w1",
                    "task": "S3",
                    "state": "running",
                },
                {
                    "schema_version": 1,
                    "ts": ANY,
                    "event": "task.state",
                    "wave": "shop_w1",
                    "task": "S3",
                    "state": "pr_open",
                },
                {
                    "schema_version": 1,
                    "ts": ANY,
                    "event": "task.state",
                    "wave": "shop_w1",
                    "task": "S6",
                    "state": "running",
                },
            ],
        )

    def test_should_record_the_task_merged_when_its_pull_request_is(self):
        # Arrange
        self.answer_pull_request_of_s3("MERGED")

        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            self.read_events("task.state")[3],
            {"schema_version": 1, "ts": ANY, "event": "task.state", "wave": "shop_w1", "task": "S3", "state": "merged"},
        )

    def test_should_park_the_task_with_the_reason_pull_request_closed_when_it_is_closed_unmerged(self):
        # Arrange
        self.answer_pull_request_of_s3("CLOSED")

        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            self.read_events("task.state")[3],
            {
                "schema_version": 1,
                "ts": ANY,
                "event": "task.state",
                "wave": "shop_w1",
                "task": "S3",
                "state": "parked",
                "reason": "pull request closed",
            },
        )

    def test_should_remove_the_worktree_of_the_task_once_its_pull_request_is_merged(self):
        # Arrange
        self.answer_pull_request_of_s3("MERGED")

        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertFalse(self.worktree.exists())
        self.assertNotIn(str(self.worktree), self.project.run_git("worktree", "list", "--porcelain"))

    def test_should_keep_the_worktree_while_a_run_holds_it(self):
        # Arrange
        self.answer_pull_request_of_s3("MERGED")
        self.configure_client_outliving_the_test()
        self.machine.run_brigade(
            CLONE_ENTRY_POINT,
            "run",
            "build-task",
            "--slot",
            "build",
            "--project",
            "shop",
            "--cwd",
            str(self.worktree),
            "--detach",
        )

        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue(self.worktree.is_dir())

    def test_should_read_the_token_of_the_login_of_the_key_cli_once_per_tick(self):
        # Arrange
        self.configure(Path(self.root.name) / "recordings", Path(self.root.name) / "instructions", CLI_KEYS)
        self.answer_pull_request_of_s3("OPEN")

        # Act
        completed = self.run_tick("--once")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            self.gh_calls.read_text().splitlines(),
            [
                "no GH_TOKEN auth token --hostname github.com --user octo-cli",
                (
                    "token-of-octo-cli pr list --head task/M1-empty-cart/S3 --state all --limit 1"
                    " --json number,state,headRefOid,baseRefName,reviewDecision,statusCheckRollup"
                ),
                "token-of-octo-cli api repos/{owner}/{repo}/compare/integration/M1-empty-cart...0123abc --jq .behind_by",
                (
                    "token-of-octo-cli pr list --head task/M1-empty-cart/S3 --state all --limit 1"
                    " --json number,state,headRefOid,baseRefName,reviewDecision,statusCheckRollup"
                ),
                "token-of-octo-cli api repos/{owner}/{repo}/compare/integration/M1-empty-cart...0123abc --jq .behind_by",
                (
                    "token-of-octo-cli pr list --head task/M1-empty-cart/S6 --state all --limit 1"
                    " --json number,state,headRefOid,baseRefName,reviewDecision,statusCheckRollup"
                ),
            ],
        )

    def test_should_wait_for_the_lock_of_the_worktrees_of_the_project_before_removing_the_worktree(self):
        # Arrange
        self.answer_pull_request_of_s3("MERGED")
        lock_file = self.state / "locks" / "worktrees-shop.lock"
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        with lock_file.open("a") as held_lock:
            fcntl.flock(held_lock, fcntl.LOCK_EX)

            # Act
            waiting = self.detect_waiting("--once")

        # Assert
        self.assertEqual((waiting, self.worktree.is_dir()), (True, True))

    def detect_waiting(self, *options: str) -> bool:
        try:
            ProcessLauncher.run(
                [sys.executable, str(CLONE_ENTRY_POINT), "tick", *options],
                capture_output=True,
                env=self.describe_environment(),
                timeout=LOCK_WAIT_S,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return True
        return False


class BrigadeTickDryRunFollowingAMergedTaskTest(FollowingTickTestCase):
    def setUp(self):
        super().setUp()
        with (self.state / "ledger" / "2026-10.jsonl").open("a") as ledger:
            ledger.write(MERGED_S3)
        self.answer_pull_request_of_s3("MERGED")

    def test_should_read_no_pull_request_once_its_worktree_is_removed(self):
        # Arrange
        self.project.run_git("worktree", "remove", str(self.worktree))

        # Act
        completed = self.run_tick("--dry-run", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertFalse(self.gh_calls.exists())

    def test_should_plan_the_removal_of_the_worktree_the_merge_left(self):
        # Act
        completed = self.run_tick("--dry-run", "--json")

        # Assert
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout)["plan"],
            [
                {"project": "shop", "task": "S3", "worktree": str(self.worktree)},
                {"wave": "shop_w1", "task": "S5", "reason": "blocked", "blockers": ["OPEN_QUESTION.Undecided"]},
                {
                    "project": "shop",
                    "wave": "shop_w1",
                    "branch": WAVE_BRANCH,
                    "task": "S4",
                },
                {
                    "project": "shop",
                    "wave": "shop_w1",
                    "branch": WAVE_BRANCH,
                    "task": "S6",
                },
            ],
        )


class BrigadeTickDryRunWithTheLoginOfTheKeyCliWithoutATokenTest(LaunchingTickTestCase):
    def test_should_plan_the_wave_while_it_follows_no_task(self):
        # Arrange
        self.configure(Path(self.root.name) / "recordings", Path(self.root.name) / "instructions", TOKENLESS_CLI_KEYS)

        # Act
        completed = self.run_tick("--dry-run", "--json")

        # Assert
        self.assertEqual((completed.returncode, completed.stderr), (0, ""))


class BrigadeTickDryRunWhereTheForgeRefusesTheReadOfOneProjectTest(FollowingTickTestCase):
    def setUp(self):
        super().setUp()
        cafe = TemporaryProject(
            Path(self.root.name).resolve() / "projects" / "cafe",
            {**self.machine.describe_environment(), **PINNED_COMMIT_DATES},
        )
        cafe.write("corpus/_schema.awawa", PROJECT_SCHEMA)
        cafe.write("corpus/tasks.awawa", MAIN_TASKS)
        cafe.track("corpus")
        cafe.run_git("commit", "--quiet", "-m", "the corpus")
        cafe.run_git("checkout", "--quiet", "-b", CAFE_BRANCH)
        cafe.write("corpus/tasks.awawa", CAFE_TASKS)
        cafe.write("corpus/milestones.awawa", CAFE_MILESTONES)
        cafe.track("corpus")
        cafe.run_git("commit", "--quiet", "-m", "the plan of M1")
        cafe.run_git("checkout", "--quiet", "main")
        self.machine.run_brigade(CLONE_ENTRY_POINT, "project", "add", str(cafe.path))
        with (self.state / "ledger" / "2026-10.jsonl").open("a") as ledger:
            ledger.write(CAFE_WAVE_STARTED)
        (self.pull_requests / "task-M1-menu-S6.refused").write_text("")

    def test_should_name_the_wave_skip_it_and_plan_the_others(self):
        # Arrange
        self.answer_pull_request_of_s3("OPEN")

        # Act
        completed = self.run_tick("--dry-run", "--json")

        # Assert
        self.assertEqual(
            (completed.returncode, completed.stderr),
            (
                0,
                (
                    "brigade tick: the wave cafe_w1 skipped: gh pr list --head task/M1-menu/S6 --state all --limit 1"
                    " --json number,state,headRefOid,baseRefName,reviewDecision,statusCheckRollup exited 1:"
                    " HTTP 502: Bad Gateway\n"
                ),
            ),
        )
        self.assertEqual(
            json.loads(completed.stdout)["plan"],
            [
                {"wave": "shop_w1", "task": "S3", "state": "pr_open", "reason": None},
                {"wave": "shop_w1", "task": "S5", "reason": "blocked", "blockers": ["OPEN_QUESTION.Undecided"]},
                {
                    "project": "shop",
                    "wave": "shop_w1",
                    "branch": WAVE_BRANCH,
                    "task": "S6",
                },
            ],
        )


TICK_FAKE_GH = (
    "#!/bin/sh\n"
    'printf \'%s\\n\' "$*" >> "{calls}"\n'
    'case "$*" in\n'
    '  "auth token"*) echo token-of-octo-cli ;;\n'
    '  "pr view"*) cat "{pull_request}" ;;\n'
    '  "pr list --head task/M1-empty-cart/S3 "*) cat "{listed}" ;;\n'
    '  "pr list"*) echo [] ;;\n'
    '  "api repos/{{owner}}/{{repo}}/compare/"*) echo 0 ;;\n'
    "esac\n"
)
PR_OPEN_LINE = (
    '{"schema_version": 1, "ts": "2026-10-17T12:01:00Z", "event": "task.state", "wave": "shop_w1", "task": "S3",'
    ' "state": "pr_open"}\n'
)


class TickPreflightTestCase(VerifyPreflightTestCase, FileWaitingTestCase):
    def setUp(self):
        super().setUp()
        install_executable(
            Path(self.root.name).resolve() / "tools" / "gh",
            TICK_FAKE_GH.format(calls=self.gh_calls, pull_request=self.pull_request, listed=self.listed),
        )
        with (self.state / "ledger" / "2026-10.jsonl").open("a") as ledger:
            ledger.write(PR_OPEN_LINE)

    def describe_pull_request(
        self,
        title: str = PULL_REQUEST_TITLE,
        body: str = PULL_REQUEST_BODY,
        check_runs: tuple = (SUCCESSFUL_CHECK_RUN,),
    ) -> None:
        super().describe_pull_request(title, body, check_runs)
        self.listed = Path(self.root.name).resolve() / "listed.json"
        self.listed.write_text(
            json.dumps(
                [
                    {
                        "number": 42,
                        "state": "OPEN",
                        "headRefOid": self.read_head(),
                        "baseRefName": WAVE_BRANCH,
                        "reviewDecision": "",
                        "statusCheckRollup": list(check_runs),
                    }
                ]
            )
        )

    def run_tick(self):
        return self.machine.run_brigade(
            CLONE_ENTRY_POINT, "tick", "--once", environment=self.describe_environment(), cwd=self.project.path
        )

    def read_events(self, name: str) -> list[dict]:
        lines = (self.state / "ledger" / "2026-10.jsonl").read_text().splitlines()
        return [event for event in map(json.loads, lines) if event["event"] == name]

    def read_last_state_of_s3(self) -> str:
        return [event for event in self.read_events("task.state") if event["task"] == "S3"][-1]["state"]

    def read_run_records(self) -> list:
        return [json.loads(path.read_text()) for path in sorted((self.state / "runs").glob("*/run.json"))]

    def read_review_run_record(self) -> dict:
        return next(record for record in self.read_run_records() if record["slot"] == "review")

    def tearDown(self):
        for record in self.read_run_records():
            self.wait_for_file(self.state / "runs" / record["run"] / "result.json")
        super().tearDown()


class BrigadeTickOnASoundPullRequestTest(TickPreflightTestCase):
    def test_should_record_the_findings_of_the_preflight_in_the_ledger(self):
        # Act
        self.run_tick()

        # Assert
        self.assertEqual(
            self.read_events("task.preflighted"),
            [
                {
                    "schema_version": 1,
                    "ts": ANY,
                    "event": "task.preflighted",
                    "project": "shop",
                    "wave": "shop_w1",
                    "task": "S3",
                    "pr": 42,
                    "head": self.read_head(),
                    "checks": [
                        {"name": "ancestry", "verdict": "pass", "findings": []},
                        {"name": "checks", "verdict": "pass", "findings": []},
                        {"name": "corpus", "verdict": "pass", "findings": []},
                        {"name": "promotion", "verdict": "pass", "findings": []},
                        {"name": "untouched_files", "verdict": "pass", "findings": []},
                        {"name": "privacy", "verdict": "pass", "findings": []},
                        {"name": "body", "verdict": "pass", "findings": []},
                        {
                            "name": "size",
                            "verdict": "info",
                            "findings": ["3 files", "9 lines", "3 packages: corpus, src/billing, src/cart", "0 layers"],
                        },
                    ],
                }
            ],
        )

    def test_should_move_the_task_to_verifying_when_no_check_fails(self):
        # Act
        self.run_tick()

        # Assert
        self.assertEqual(self.read_last_state_of_s3(), "verifying")

    def test_should_launch_the_verification_of_the_pull_request_on_the_review_slot(self):
        # Act
        self.run_tick()

        # Assert
        self.assertEqual(
            self.read_review_run_record(),
            {
                "schema_version": 1,
                "run": ANY,
                "procedure": "verify-pr",
                "procedure_path": str(REPOSITORY_ROOT / "brigade" / "runs" / "data" / "procedures" / "verify-pr.md"),
                "slot": "review",
                "role": "reviewer",
                "role_source": "built-in",
                "client": "fake",
                "project": "shop",
                "cwd": str(self.worktree),
                "worktree": ANY,
                "capabilities": ["read", "shell"],
                "budget": 40,
                "wall_limit_s": 1500,
                "arguments": {"pr": "42", "task": "@TASK.S3"},
                "wave": "shop_w1",
                "task": "S3",
                "brief": None,
            },
        )


class BrigadeTickOnAPullRequestOfAProjectWithoutCheckRunsTest(TickPreflightTestCase):
    def setUp(self):
        super().setUp()
        (self.machine.corpus / "projects.awawa").write_text(
            f'PROJECT shop\n\tPATH "{self.project.path}"\n\tMAIN "main"\n\tCORPUS "corpus"\n'
            '\tACCEPTANCE "python3 -m unittest"\n\tHEAVY "python3 -m unittest discover tests/e2e"\n\tFORGE "none"\n'
            "\tCHECK_RUNS none\n\tSTATUS active\n"
        )
        self.describe_pull_request(check_runs=())

    def test_should_move_the_task_to_verifying_with_no_check_run(self):
        # Act
        self.run_tick()

        # Assert
        self.assertEqual(self.read_last_state_of_s3(), "verifying")


class BrigadeTickOnAPullRequestWithAFailingCheckTest(TickPreflightTestCase):
    def setUp(self):
        super().setUp()
        self.describe_pull_request(body="Empty the cart in one click\n\n$checks\n")

    def test_should_hand_the_task_to_a_remediation_run_in_fixing(self):
        # Act
        self.run_tick()

        # Assert
        self.assertEqual(self.read_last_state_of_s3(), "fixing")

    def test_should_run_the_preflight_of_a_head_once(self):
        # Arrange
        self.run_tick()

        # Act
        self.run_tick()

        # Assert
        self.assertEqual(len(self.read_events("task.preflighted")), 1)


class BrigadeTickOnAPullRequestNoTaskOpenedTest(TickPreflightTestCase):
    def setUp(self):
        super().setUp()
        self.listed.write_text(
            json.dumps(
                [
                    {
                        "number": 43,
                        "state": "OPEN",
                        "headRefOid": self.read_head(),
                        "baseRefName": WAVE_BRANCH,
                        "reviewDecision": "",
                        "statusCheckRollup": [SUCCESSFUL_CHECK_RUN],
                    }
                ]
            )
        )

    def test_should_not_run_the_preflight_of_a_pull_request_the_task_did_not_open(self):
        # Act
        self.run_tick()

        # Assert
        self.assertEqual(self.read_events("task.preflighted"), [])


MAIN_TASKS_WITH_A_CANDIDATE = MAIN_TASKS + '\nTASK S7\n\tTITLE "Save the cart for later"\n\tSTATUS todo\n'
NO_WAVE_EVENTS = ""


class BrigadeTickOnceWithACandidateOutsideEveryOpenWaveTest(LaunchingTickTestCase):
    def setUp(self):
        super().setUp()
        self.project.write("corpus/tasks.awawa", MAIN_TASKS_WITH_A_CANDIDATE)
        self.project.track("corpus")
        self.project.run_git("commit", "--quiet", "-m", "a task to deliver")
        (self.state / "ledger" / "2026-10.jsonl").write_text(NO_WAVE_EVENTS)

    def test_should_start_a_wave_of_the_candidate_under_no_policy(self):
        # Act
        self.run_tick("--once")

        # Assert
        self.assertEqual(
            self.read_events("wave.started"),
            [
                {
                    "schema_version": 2,
                    "ts": ANY,
                    "event": "wave.started",
                    "wave": "shop_w1",
                    "project": "shop",
                    "branch": "integration/shop_w1",
                    "tasks": ["S7"],
                }
            ],
        )

    def test_should_cut_the_branch_of_the_wave_it_starts(self):
        # Act
        self.run_tick("--once")

        # Assert
        self.assertEqual(
            self.project.run_git("branch", "--list", "--format=%(refname:short)", "integration/shop_w1"),
            "integration/shop_w1\n",
        )
