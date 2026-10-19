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
from tests.unit.create_test_runtime import create_test_paths, create_test_runtime
from tests.unit.recording_process_runner import RecordingProcessRunner
from tests.unit.runs.create_run_plan import RUN_ID, create_run_plan
from tests.unit.runs.test_run_segment import ClientDouble, SpawnDouble


class ClientAnsweringOutcomesDouble(ClientDouble):
    def __init__(self, outcomes: list[str]):
        super().__init__()
        self.outcomes = outcomes

    def answer(self, operation: str, request: dict) -> dict:
        document = super().answer(operation, request)
        if operation == "parse-result":
            return {**document, "outcome": self.outcomes.pop(0)}
        return document


class RunSegmentsTestCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        self.paths = create_test_paths(self.root)
        self.git = RecordingProcessRunner()
        self.runtime = create_test_runtime(self.paths, run_process=self.git, spawn_process=SpawnDouble().spawn)
        (self.root / "project").mkdir()

    def run_plan(self, outcomes: list[str], **changes):
        plan = create_run_plan(self.root, client_adapter=ClientAnsweringOutcomesDouble(outcomes), **changes)
        plan.run_directory.mkdir(parents=True)
        ask_progress(plan, "create_document", self.runtime)
        return plan, run_segments(plan, self.runtime, StopSignalReceiver())

    def read_signals(self) -> list[SignalRecorded]:
        return [
            entry.event
            for entry in read_ledger(self.paths.state_root).entries
            if isinstance(entry.event, SignalRecorded)
        ]


class RunSegmentsOfARunDoneInOneSegmentTest(RunSegmentsTestCase):
    def test_should_keep_the_result_of_its_segment_as_the_result_of_the_run(self):
        # Act
        plan, records = self.run_plan(["done"])

        # Assert
        self.assertEqual(
            (
                [record.outcome for record in records],
                json.loads((plan.run_directory / "result.json").read_text())["outcome"],
            ),
            (["done"], "done"),
        )


class RunSegmentsOfARunHandedOverTest(RunSegmentsTestCase):
    def test_should_record_the_hand_over_and_stop_without_progress_to_resume_from(self):
        # Act
        _, records = self.run_plan(["handed_over"], handovers=1)

        # Assert
        self.assertEqual(
            ([record.outcome for record in records], self.read_signals()),
            (
                ["handed_over"],
                [
                    SignalRecorded(
                        signal="handed_over",
                        project=None,
                        procedure="build-task",
                        run=RUN_ID,
                        segment=1,
                        budget=40,
                    )
                ],
            ),
        )

    def test_should_stop_once_the_hand_overs_are_spent(self):
        # Act
        _, records = self.run_plan(["handed_over"], handovers=0)

        # Assert
        self.assertEqual(len(records), 1)


class RunSegmentsOverItsBudgetTest(RunSegmentsTestCase):
    def test_should_record_the_steps_beyond_the_budget(self):
        # Arrange
        procedure = Procedure(
            name="build-task", location="built-in", argument="build-task", capabilities=("read",), budget=5, body="."
        )

        # Act
        self.run_plan(["done"], procedure=procedure)

        # Assert
        self.assertEqual(
            self.read_signals(),
            [
                SignalRecorded(
                    signal="budget_exceeded",
                    project=None,
                    procedure="build-task",
                    run=RUN_ID,
                    segment=1,
                    budget=5,
                    steps=12,
                )
            ],
        )


class RunSegmentsInADisposableWorktreeTest(RunSegmentsTestCase):
    def test_should_add_the_worktree_before_and_remove_it_after_under_the_lock_of_the_project(self):
        for project in [None, "shop"]:
            with self.subTest(project=project):
                # Arrange
                self.git.requests.clear()
                worktree = self.root / "state" / "runs" / RUN_ID / "worktree"

                # Act
                plan, _ = self.run_plan(["done"], disposable_worktree=True, worktree=worktree, project=project)
                shutil.rmtree(plan.run_directory)

                # Assert
                self.assertEqual(
                    [argv for _, argv in self.git.commands],
                    [
                        ("git", "worktree", "add", "--quiet", "--detach", str(worktree), "HEAD"),
                        ("git", "worktree", "remove", "--force", str(worktree)),
                    ],
                )
