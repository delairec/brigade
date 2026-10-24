import json
import shutil
import signal
import tempfile
import unittest
from pathlib import Path

from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.signal_recorded import SignalRecorded
from brigade.runs.ask_progress import ask_progress
from brigade.runs.resolve_procedure import Procedure
from brigade.runs.run_segments import run_segments
from brigade.system.stop_signal_receiver import StopSignalReceiver
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.recording_process_runner import RecordingProcessRunner
from tests.unit.runs.create_run_plan import RUN_ID, create_run_plan

PID_HELD_BY_NO_PROCESS = 2**31 - 1
LIMIT_ALREADY_REACHED_S = 0.0
LAUNCH_OPERATIONS = ("launch-argv", "resume-argv")
RATE_LIMITED_SESSION = "rate-limited-session"
NO_SESSION_TO_RESUME = None
TASK_BRIEF = "Deliver S3 behind the feature flag of the shop.\n"
PROGRESS_OF_THE_FIRST_SEGMENT = "- the first segment is done\n"
LAUNCH = {
    "schema_version": 1,
    "argv": ["double-client", "--print"],
    "environment": {},
    "stdin": "the brief of the run",
    "session_id": None,
}


class ClientAnsweringOutcomesDouble:
    def __init__(self, outcomes: list[str]):
        self.outcomes = outcomes

    def answer(self, operation: str, request: dict) -> dict:
        if operation == "launch-argv":
            return LAUNCH
        return {
            "schema_version": 1,
            "outcome": self.outcomes.pop(0),
            "steps": 12,
            "usage": None,
            "session_id": "session-b73",
            "duration_ms": 4200,
            "cost_usd": None,
            "error_class": None,
            "reset": None,
            "message": None,
        }


class ExitedProcessDouble:
    pid = 4242

    def wait(self, **_limit) -> int:
        return 0


def spawn_an_exited_client(request) -> ExitedProcessDouble:
    request.stdout.write_text("the client finished the task", encoding="utf-8")
    request.stderr.write_text("", encoding="utf-8")
    return ExitedProcessDouble()


class RunSegmentsTestCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        self.paths = create_test_paths(self.root)
        self.git = RecordingProcessRunner()
        self.runtime = create_test_runtime(self.paths, run_process=self.git, spawn_process=spawn_an_exited_client)
        (self.root / "project").mkdir()

    def create_plan(self, outcomes: list[str], progress: str | None = None, **changes):
        plan = create_run_plan(self.root, client_adapter=ClientAnsweringOutcomesDouble(outcomes), **changes)
        plan.run_directory.mkdir(parents=True)
        ask_progress(plan, "create_document", self.runtime)
        if progress is not None:
            plan.progress_file.write_text(progress)
        return plan


class RunSegmentsOfARunDoneInOneSegmentTest(RunSegmentsTestCase):
    def test_should_keep_the_result_of_its_segment_as_the_result_of_the_run(self):
        # Arrange
        plan = self.create_plan(["done"])

        # Act
        records = run_segments(plan, self.runtime, StopSignalReceiver())

        # Assert
        self.assertEqual(records[-1].number, 1)
        self.assertEqual(json.loads((plan.run_directory / "result.json").read_text())["outcome"], "done")


class RunSegmentsOfARunHandedOverTest(RunSegmentsTestCase):
    def test_should_record_the_hand_over_and_stop_without_progress_to_resume_from(self):
        # Arrange
        plan = self.create_plan(["handed_over"], handovers=1)

        # Act
        records = run_segments(plan, self.runtime, StopSignalReceiver())

        # Assert
        self.assertEqual(records[-1].number, 1)
        self.assertEqual(
            read_ledger(self.paths.state_root).entries[1].event,
            SignalRecorded(
                signal="handed_over", project=None, procedure="build-task", run=RUN_ID, segment=1, budget=40
            ),
        )

    def test_should_stop_once_the_hand_overs_are_spent(self):
        # Arrange
        plan = self.create_plan(["handed_over"], progress="- the test is written\n", handovers=0)

        # Act
        records = run_segments(plan, self.runtime, StopSignalReceiver())

        # Assert
        self.assertEqual(records[-1].number, 1)

    def test_should_run_a_next_segment_while_the_progress_file_holds_an_entry(self):
        # Arrange
        plan = self.create_plan(["handed_over", "done"], progress="- the test is written\n", handovers=1)

        # Act
        records = run_segments(plan, self.runtime, StopSignalReceiver())

        # Assert
        self.assertEqual(records[0].number, 1)
        self.assertEqual(records[0].outcome, "handed_over")
        self.assertEqual(records[1].number, 2)
        self.assertEqual(records[1].outcome, "done")


class ClientRecordingLaunchesDouble(ClientAnsweringOutcomesDouble):
    def __init__(self, outcomes: list[str]):
        super().__init__(outcomes)
        self.launches = []

    def answer(self, operation: str, request: dict) -> dict:
        if operation in LAUNCH_OPERATIONS:
            self.launches.append(request)
            return LAUNCH
        return super().answer(operation, request)


class RunSegmentsOfAResumedRunTest(RunSegmentsTestCase):
    def create_resumed_plan(self, client: ClientRecordingLaunchesDouble, resumed_session: str | None):
        plan = create_run_plan(
            self.root,
            client_adapter=client,
            first_segment=2,
            resumed_session=resumed_session,
            handovers=2,
            brief=TASK_BRIEF,
        )
        plan.run_directory.mkdir(parents=True)
        ask_progress(plan, "create_document", self.runtime)
        plan.progress_file.write_text(PROGRESS_OF_THE_FIRST_SEGMENT)
        return plan

    def test_should_resume_its_first_segment_in_the_session_it_left_and_the_next_in_one_of_its_own(self):
        # Arrange
        client = ClientRecordingLaunchesDouble(["handed_over", "done"])
        plan = self.create_resumed_plan(client, RATE_LIMITED_SESSION)

        # Act
        run_segments(plan, self.runtime, StopSignalReceiver())

        # Assert
        self.assertEqual(client.launches[0]["session_id"], "rate-limited-session")
        self.assertNotEqual(client.launches[1]["session_id"], "rate-limited-session")

    def test_should_relaunch_a_run_without_its_session_on_a_brief_opening_on_its_progress(self):
        # Arrange
        client = ClientRecordingLaunchesDouble(["done"])
        plan = self.create_resumed_plan(client, NO_SESSION_TO_RESUME)

        # Act
        records = run_segments(plan, self.runtime, StopSignalReceiver())

        # Assert
        self.assertEqual(records[0].number, 2)
        self.assertEqual(records[0].outcome, "done")
        self.assertRegex(client.launches[0]["brief"], r"^# Progress so far\n\n- the first segment is done\n")
        self.assertIn("# Brief\n\nDeliver S3 behind the feature flag of the shop.\n", client.launches[0]["brief"])


class ProcessCutAtTheLimitDouble:
    pid = PID_HELD_BY_NO_PROCESS

    def wait(self, timeout: float) -> int:
        return -signal.SIGTERM


def spawn_a_client_outliving_the_limit(request) -> ProcessCutAtTheLimitDouble:
    request.stdout.write_text("Reading the task\n", encoding="utf-8")
    request.stderr.write_text("", encoding="utf-8")
    return ProcessCutAtTheLimitDouble()


class RunSegmentsCutOnTheClockTest(RunSegmentsTestCase):
    def setUp(self):
        super().setUp()
        self.runtime = create_test_runtime(
            self.paths, run_process=self.git, spawn_process=spawn_a_client_outliving_the_limit
        )

    def test_should_record_that_the_clock_cut_the_segment_at_the_wall_time_limit(self):
        # Arrange
        plan = self.create_plan(["done"], wall_limit_s=LIMIT_ALREADY_REACHED_S)

        # Act
        run_segments(plan, self.runtime, StopSignalReceiver())

        # Assert
        self.assertEqual(
            read_ledger(self.paths.state_root).entries[1].event,
            SignalRecorded(
                signal="wall_limit_reached",
                project=None,
                procedure="build-task",
                run=RUN_ID,
                segment=1,
                budget=40,
                wall_limit_s=0.0,
            ),
        )

    def test_should_relaunch_a_segment_cut_on_the_clock_with_progress_up_to_the_last_hand_over(self):
        # Arrange
        plan = self.create_plan(
            ["done"], progress="- the test is written\n", handovers=2, wall_limit_s=LIMIT_ALREADY_REACHED_S
        )

        # Act
        records = run_segments(plan, self.runtime, StopSignalReceiver())

        # Assert
        self.assertEqual(records[-1].number, 3)
        self.assertEqual(records[-1].outcome, "wall_limit")


class RunSegmentsStoppedAtTheSoftLimitTest(RunSegmentsTestCase):
    def test_should_record_that_the_clock_ended_the_segment_with_its_wall_time_limit(self):
        # Arrange
        plan = self.create_plan(["soft_limit"], wall_limit_s=4.0)

        # Act
        run_segments(plan, self.runtime, StopSignalReceiver())

        # Assert
        self.assertEqual(
            read_ledger(self.paths.state_root).entries[1].event,
            SignalRecorded(
                signal="wall_limit_reached",
                project=None,
                procedure="build-task",
                run=RUN_ID,
                segment=1,
                budget=40,
                wall_limit_s=4.0,
            ),
        )

    def test_should_resume_a_segment_stopped_at_the_soft_limit_with_progress(self):
        # Arrange
        plan = self.create_plan(["soft_limit", "done"], progress="- the test is written\n", handovers=1)

        # Act
        records = run_segments(plan, self.runtime, StopSignalReceiver())

        # Assert
        self.assertEqual(records[-1].number, 2)
        self.assertEqual(records[-1].outcome, "done")


class RunSegmentsOverItsBudgetTest(RunSegmentsTestCase):
    def test_should_record_the_steps_beyond_the_budget(self):
        # Arrange
        procedure = Procedure(
            name="build-task", location="built-in", argument="build-task", capabilities=("read",), budget=5, body="."
        )
        plan = self.create_plan(["done"], procedure=procedure)

        # Act
        run_segments(plan, self.runtime, StopSignalReceiver())

        # Assert
        self.assertEqual(
            read_ledger(self.paths.state_root).entries[1].event,
            SignalRecorded(
                signal="budget_exceeded",
                project=None,
                procedure="build-task",
                run=RUN_ID,
                segment=1,
                budget=5,
                steps=12,
            ),
        )


class RunSegmentsInADisposableWorktreeTest(RunSegmentsTestCase):
    def setUp(self):
        super().setUp()
        self.worktree = self.root / "state" / "runs" / RUN_ID / "worktree"
        self.project = str(self.root / "project")

    def test_should_add_the_worktree_before_and_remove_it_after(self):
        # Arrange
        plan = self.create_plan(["done"], disposable_worktree=True, worktree=self.worktree)

        # Act
        run_segments(plan, self.runtime, StopSignalReceiver())

        # Assert
        self.assertEqual(
            self.git.commands,
            [
                (self.project, ("git", "worktree", "add", "--quiet", "--detach", str(self.worktree), "HEAD")),
                (self.project, ("git", "worktree", "remove", "--force", str(self.worktree))),
            ],
        )

    def test_should_hold_the_worktrees_lock_of_the_project_while_adding_and_removing_it(self):
        # Arrange
        plan = self.create_plan(["done"], disposable_worktree=True, worktree=self.worktree, project="shop")

        # Act
        run_segments(plan, self.runtime, StopSignalReceiver())

        # Assert
        self.assertCountEqual(
            self.paths.lock_directory.iterdir(),
            [self.paths.lock_directory / "ledger.lock", self.paths.lock_directory / "worktrees-shop.lock"],
        )
