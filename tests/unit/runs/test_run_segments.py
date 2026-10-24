import json
import shutil
import signal
import tempfile
import unittest
from pathlib import Path

from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.run_finished import RunFinished
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
REPORTED_USAGE = {
    "input_tokens": 120,
    "output_tokens": 3400,
    "cache_creation_input_tokens": 16778,
    "cache_read_input_tokens": 98000,
}
PROCEDURE_OF_FIVE_STEPS = Procedure(
    name="build-task", location="built-in", argument="build-task", capabilities=("read",), budget=5, body="."
)
PROCEDURE_OF_TWELVE_STEPS = Procedure(
    name="build-task", location="built-in", argument="build-task", capabilities=("read",), budget=12, body="."
)
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

    def create_plan(
        self, outcomes: list[str], progress: str | None = None, client_double=ClientAnsweringOutcomesDouble, **changes
    ):
        plan = create_run_plan(self.root, client_adapter=client_double(outcomes), **changes)
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
        plan = self.create_plan(["done"], procedure=PROCEDURE_OF_FIVE_STEPS)

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

    def test_should_record_no_signal_for_a_segment_at_exactly_its_budget(self):
        # Arrange
        plan = self.create_plan(["done"], procedure=PROCEDURE_OF_TWELVE_STEPS)

        # Act
        run_segments(plan, self.runtime, StopSignalReceiver())

        # Assert
        self.assertEqual(len(read_ledger(self.paths.state_root).entries), 1)

    def test_should_record_no_signal_for_the_steps_of_a_client_that_counts_none(self):
        # Arrange
        plan = self.create_plan(["done"], procedure=PROCEDURE_OF_FIVE_STEPS, counts_steps=False)

        # Act
        run_segments(plan, self.runtime, StopSignalReceiver())

        # Assert
        self.assertEqual(len(read_ledger(self.paths.state_root).entries), 1)


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

    def test_should_hold_no_worktrees_lock_for_a_run_outside_any_project(self):
        # Arrange
        plan = self.create_plan(["done"], disposable_worktree=True, worktree=self.worktree)

        # Act
        run_segments(plan, self.runtime, StopSignalReceiver())

        # Assert
        self.assertEqual(list(self.paths.lock_directory.iterdir()), [self.paths.lock_directory / "ledger.lock"])


class ClientReportingUsageDouble(ClientAnsweringOutcomesDouble):
    def answer(self, operation: str, request: dict) -> dict:
        answer = super().answer(operation, request)
        if operation == "launch-argv":
            return answer
        return {**answer, "usage": REPORTED_USAGE}


class ClientFailingOnAnErrorClassDouble(ClientAnsweringOutcomesDouble):
    def answer(self, operation: str, request: dict) -> dict:
        answer = super().answer(operation, request)
        if operation == "launch-argv":
            return answer
        return {**answer, "outcome": "failed", "error_class": answer["outcome"]}


class RunSegmentsOfARunReportingItsStepsAndUsageTest(RunSegmentsTestCase):
    def read_ledger_lines(self) -> list[dict]:
        [ledger_file] = (self.paths.state_root / "ledger").glob("*.jsonl")
        return list(map(json.loads, ledger_file.read_text().splitlines()))

    def test_should_append_the_finished_run_to_the_ledger(self):
        # Arrange
        plan = self.create_plan(["done"], client_double=ClientReportingUsageDouble)

        # Act
        run_segments(plan, self.runtime, StopSignalReceiver())

        # Assert
        self.assertEqual(
            self.read_ledger_lines(),
            [
                {
                    "schema_version": 2,
                    "ts": "2026-10-19T09:00:00Z",
                    "event": "run.finished",
                    "run": RUN_ID,
                    "segment": 1,
                    "procedure": "build-task",
                    "slot": "build",
                    "role": "builder",
                    "client": "fake",
                    "project": None,
                    "session": "session-b73",
                    "main_steps": 12,
                    "total_steps": None,
                    "usage": REPORTED_USAGE,
                    "outcome": "done",
                    "error_class": None,
                    "exit": 0,
                    "wave": None,
                    "task": None,
                    "duration_ms": 0,
                    "nulls": {
                        "project": "no project given",
                        "wave": "not launched by a wave",
                        "task": "not launched for a task",
                        "total_steps": "the client reads no transcript",
                        "error_class": "the run did not fail",
                    },
                }
            ],
        )

    def test_should_keep_the_line_the_ledger_appended_as_the_result_of_the_segment_and_of_the_run(self):
        # Arrange
        plan = self.create_plan(["done"], client_double=ClientReportingUsageDouble)

        # Act
        run_segments(plan, self.runtime, StopSignalReceiver())

        # Assert
        [finished] = self.read_ledger_lines()
        self.assertEqual(json.loads((plan.run_directory / "segments" / "1" / "result.json").read_text()), finished)
        self.assertEqual(json.loads((plan.run_directory / "result.json").read_text()), finished)


class RunSegmentsOfARunEndedOnTheStepCapTest(RunSegmentsTestCase):
    def test_should_relaunch_a_segment_ended_on_the_step_cap_with_progress_up_to_the_last_hand_over(self):
        # Arrange
        plan = self.create_plan(
            ["turn_limit", "turn_limit", "turn_limit"],
            progress=PROGRESS_OF_THE_FIRST_SEGMENT,
            handovers=2,
            client_double=ClientFailingOnAnErrorClassDouble,
        )

        # Act
        records = run_segments(plan, self.runtime, StopSignalReceiver())

        # Assert
        self.assertEqual(records[-1].number, 3)
        self.assertEqual(records[-1].outcome, "turn_limit")

    def test_should_append_one_finished_run_per_segment(self):
        # Arrange
        plan = self.create_plan(
            ["turn_limit", "turn_limit", "turn_limit"],
            progress=PROGRESS_OF_THE_FIRST_SEGMENT,
            handovers=2,
            client_double=ClientFailingOnAnErrorClassDouble,
        )

        # Act
        run_segments(plan, self.runtime, StopSignalReceiver())

        # Assert
        entries = read_ledger(self.paths.state_root).entries
        self.assertEqual(
            [
                (type(entries[0].event), entries[0].event.segment),
                (type(entries[2].event), entries[2].event.segment),
                (type(entries[4].event), entries[4].event.segment),
            ],
            [(RunFinished, 1), (RunFinished, 2), (RunFinished, 3)],
        )

    def test_should_not_relaunch_a_segment_ended_on_the_step_cap_with_an_empty_progress_file(self):
        # Arrange
        plan = self.create_plan(["turn_limit", "done"], handovers=2, client_double=ClientFailingOnAnErrorClassDouble)

        # Act
        records = run_segments(plan, self.runtime, StopSignalReceiver())

        # Assert
        self.assertEqual(records[-1].number, 1)

    def test_should_record_the_budget_exceeded_then_the_step_cap_reached(self):
        # Arrange
        plan = self.create_plan(
            ["turn_limit"], procedure=PROCEDURE_OF_FIVE_STEPS, client_double=ClientFailingOnAnErrorClassDouble
        )

        # Act
        run_segments(plan, self.runtime, StopSignalReceiver())

        # Assert
        [_started, exceeded, reached] = read_ledger(self.paths.state_root).entries
        self.assertEqual(
            [exceeded.event, reached.event],
            [
                SignalRecorded(
                    signal="budget_exceeded",
                    project=None,
                    procedure="build-task",
                    run=RUN_ID,
                    segment=1,
                    budget=5,
                    steps=12,
                ),
                SignalRecorded(
                    signal="budget_reached", project=None, procedure="build-task", run=RUN_ID, segment=1, budget=5
                ),
            ],
        )

    def test_should_keep_the_step_cap_as_the_outcome_of_the_run(self):
        # Arrange
        plan = self.create_plan(["turn_limit"], client_double=ClientFailingOnAnErrorClassDouble)

        # Act
        run_segments(plan, self.runtime, StopSignalReceiver())

        # Assert
        self.assertEqual(json.loads((plan.run_directory / "result.json").read_text())["outcome"], "turn_limit")


class RunSegmentsOfARunHandedOverAtEverySegmentTest(RunSegmentsTestCase):
    def test_should_stop_on_the_hand_over_of_the_last_segment(self):
        # Arrange
        plan = self.create_plan(
            ["handed_over", "handed_over", "handed_over"], progress=PROGRESS_OF_THE_FIRST_SEGMENT, handovers=2
        )

        # Act
        records = run_segments(plan, self.runtime, StopSignalReceiver())

        # Assert
        self.assertEqual(records[-1].number, 3)
        self.assertEqual(records[-1].outcome, "handed_over")

    def test_should_open_the_brief_of_the_next_segment_on_the_progress_file(self):
        # Arrange
        client = ClientRecordingLaunchesDouble(["handed_over", "done"])
        plan = create_run_plan(self.root, client_adapter=client, handovers=1)
        plan.run_directory.mkdir(parents=True)
        ask_progress(plan, "create_document", self.runtime)
        plan.progress_file.write_text(PROGRESS_OF_THE_FIRST_SEGMENT)

        # Act
        run_segments(plan, self.runtime, StopSignalReceiver())

        # Assert
        self.assertEqual(
            client.launches[1]["brief"],
            "# Progress so far\n\n"
            "- the first segment is done\n\n"
            "# Procedure build-task\n\n"
            "Deliver the task.\n\n"
            "# Progress file\n\n"
            f"The progress is the Markdown file {plan.progress_file}.\n\n"
            "- one entry per major step: what it did in one line, the facts it established, one line each and five"
            " at most, and the next step as the procedure names it, complete at the end\n"
            "- a fact is what the next segment needs and no command gives back\n"
            "- never command output, a diff, the course of the step, a restatement of the brief or a fact an earlier"
            " entry holds\n"
            "- a handover entry holds what remains, one line per step not done, and the next step\n\n"
            "# End of segment\n\n"
            "End your final message on one of these lines: brigade-end: done once the work is delivered,"
            " brigade-end: handed_over when a next segment resumes it from the progress file,"
            " brigade-end: blocked when it waits for a ruling.\n",
        )


class RunSegmentsOfASegmentEndedWithoutDeclarationTest(RunSegmentsTestCase):
    def test_should_relaunch_an_undeclared_segment_with_progress_up_to_the_last_hand_over(self):
        # Arrange
        plan = self.create_plan(
            ["undeclared", "undeclared", "undeclared"], progress=PROGRESS_OF_THE_FIRST_SEGMENT, handovers=2
        )

        # Act
        records = run_segments(plan, self.runtime, StopSignalReceiver())

        # Assert
        self.assertEqual(records[-1].number, 3)
        self.assertEqual(records[-1].outcome, "undeclared")

    def test_should_not_relaunch_an_undeclared_segment_with_an_empty_progress_file(self):
        # Arrange
        plan = self.create_plan(["undeclared", "done"], handovers=2)

        # Act
        records = run_segments(plan, self.runtime, StopSignalReceiver())

        # Assert
        self.assertEqual(records[-1].number, 1)

    def test_should_record_that_the_segment_ended_undeclared(self):
        # Arrange
        plan = self.create_plan(["undeclared"])

        # Act
        run_segments(plan, self.runtime, StopSignalReceiver())

        # Assert
        self.assertEqual(
            read_ledger(self.paths.state_root).entries[1].event,
            SignalRecorded(signal="undeclared", project=None, procedure="build-task", run=RUN_ID, segment=1, budget=40),
        )


class RunSegmentsOfASegmentEndedWithoutRelaunchTest(RunSegmentsTestCase):
    def test_should_stop_after_one_segment_whatever_its_progress(self):
        # Arrange
        rows = [
            ("blocked", "blocked", ClientAnsweringOutcomesDouble),
            ("failed on a client error", "execution", ClientFailingOnAnErrorClassDouble),
        ]
        for case, outcome, client_double in rows:
            with self.subTest(case=case):
                # Arrange
                shutil.rmtree(self.root / "state", ignore_errors=True)
                plan = self.create_plan(
                    [outcome, "done"], progress=PROGRESS_OF_THE_FIRST_SEGMENT, handovers=2, client_double=client_double
                )

                # Act
                records = run_segments(plan, self.runtime, StopSignalReceiver())

                # Assert
                self.assertEqual(records[-1].number, 1)
