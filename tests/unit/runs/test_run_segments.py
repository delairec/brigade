import json
import shutil
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
        self.assertEqual(
            (records[-1].number, json.loads((plan.run_directory / "result.json").read_text())["outcome"]),
            (1, "done"),
        )


class RunSegmentsOfARunHandedOverTest(RunSegmentsTestCase):
    def test_should_record_the_hand_over_and_stop_without_progress_to_resume_from(self):
        # Arrange
        plan = self.create_plan(["handed_over"], handovers=1)

        # Act
        records = run_segments(plan, self.runtime, StopSignalReceiver())

        # Assert
        self.assertEqual(
            (records[-1].number, read_ledger(self.paths.state_root).entries[1].event),
            (
                1,
                SignalRecorded(
                    signal="handed_over", project=None, procedure="build-task", run=RUN_ID, segment=1, budget=40
                ),
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
        self.assertEqual(
            ((records[0].number, records[0].outcome), (records[1].number, records[1].outcome)),
            ((1, "handed_over"), (2, "done")),
        )


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
        self.assertEqual(
            list(self.paths.lock_directory.iterdir()),
            [self.paths.lock_directory / "ledger.lock", self.paths.lock_directory / "worktrees-shop.lock"],
        )
