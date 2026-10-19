import os
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest import mock

from brigade.errors import BrigadeError
from brigade.ledger.append_event import append_event
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.order_done import OrderDone
from brigade.ledger.order_parked import OrderParked
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.step_done import StepDone
from brigade.ledger.step_failed import StepFailed
from brigade.runs.record_run_pid import record_run_pid
from brigade.studies.convert_study import Study
from brigade.studies.run_study import run_study
from tests.unit.create_scripted_runtime import RUNTIME_NOW, create_scripted_runtime
from tests.unit.scripted_processes import ScriptedProcesses
from tests.unit.studies.create_study_equipment import create_study_equipment

RUN_ID = "20261019T090000Z-aaaaaa"
ANSWER = 'FINDING trees_20261019T090000Z_aaaaaa\n\tSTUDY "trees"\n\tRUN "20261019T090000Z-aaaaaa"\n'
EARLIER = datetime(2026, 10, 18, 7, 0, tzinfo=UTC)
SCAN = Study(
    name="trees",
    project=None,
    question=None,
    collectors=(),
    slot="none",
    every=None,
    output="entity:FINDING",
    answer_type="FINDING",
    status="active",
)
SCAN_OF_A_MISSING_COLLECTOR = Study(
    name="trees",
    project=None,
    question=None,
    collectors=("weather",),
    slot="none",
    every=None,
    output="entity:FINDING",
    answer_type="FINDING",
    status="active",
)
SCAN_INTO_THE_INBOX = Study(
    name="trees",
    project=None,
    question=None,
    collectors=(),
    slot="none",
    every=None,
    output="inbox",
    answer_type="FINDING",
    status="active",
)


def refuse_collector(name: str, project: Path):
    raise BrigadeError(f"no collector {name}")


class RunStudyArrangement:
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.processes = ScriptedProcesses()
        self.runtime = create_scripted_runtime(self.root, self.processes)
        self.equipment = create_study_equipment(resolve_collector=refuse_collector)
        self.config_root = self.runtime.paths.config_root
        self.processes.answer_corpus_change(
            self.config_root, ("findings.awawa",), "brigade study run: the answer of @STUDY.trees"
        )

    def record_order(self, event) -> None:
        append_event(self.runtime.paths, EARLIER, event)

    def create_live_run(self, run: str, study: str) -> None:
        run_directory = self.root / "state" / "runs" / run
        run_directory.mkdir(parents=True)
        (run_directory / "study.json").write_text(f'{{"study": "{study}"}}', encoding="utf-8")
        record_run_pid(run_directory, os.getpid())


class RunStudyTest(RunStudyArrangement, unittest.TestCase):
    def test_should_answer_the_run_done(self):
        # Act
        ran = run_study(self.runtime, SCAN, self.equipment, RUN_ID)

        # Assert
        self.assertEqual(ran, {"study": "trees", "run": RUN_ID, "state": "done"})

    def test_should_write_the_answer_of_the_study(self):
        # Act
        run_study(self.runtime, SCAN, self.equipment, RUN_ID)

        # Assert
        self.assertEqual((self.config_root / "findings.awawa").read_text(encoding="utf-8"), ANSWER)

    def test_should_record_each_step_and_the_order_done(self):
        # Act
        run_study(self.runtime, SCAN, self.equipment, RUN_ID)

        # Assert
        self.assertEqual(
            read_ledger(self.root / "state").entries,
            (
                LedgerEntry(instant=RUNTIME_NOW, event=StepDone(kind="study", run=RUN_ID, step="collect")),
                LedgerEntry(instant=RUNTIME_NOW, event=StepDone(kind="study", run=RUN_ID, step="judge")),
                LedgerEntry(instant=RUNTIME_NOW, event=StepDone(kind="study", run=RUN_ID, step="output")),
                LedgerEntry(
                    instant=RUNTIME_NOW, event=OrderDone(project=None, kind="study", order="trees", run=RUN_ID)
                ),
            ),
        )

    def test_should_resume_a_run_past_the_steps_it_completed(self):
        # Arrange
        steps = self.root / "state" / "runs" / RUN_ID / "steps"
        steps.mkdir(parents=True)
        (steps / "collect.json").write_text('{"collected": []}', encoding="utf-8")

        # Act
        ran = run_study(self.runtime, SCAN_OF_A_MISSING_COLLECTOR, self.equipment, RUN_ID)

        # Assert
        self.assertEqual(ran, {"study": "trees", "run": RUN_ID, "state": "done"})

    def test_should_resume_the_parked_run_of_the_study(self):
        # Arrange
        self.record_order(
            OrderParked(project=None, kind="study", order="trees", run=RUN_ID, step="collect", reason="quota")
        )
        self.record_order(OrderDone(project=None, kind="study", order="ash", run="20261018T070000Z-bbbbbb"))

        # Act
        ran = run_study(self.runtime, SCAN, self.equipment, None)

        # Assert
        self.assertEqual(ran["run"], RUN_ID)

    def test_should_run_a_study_while_another_study_runs(self):
        # Arrange
        self.create_live_run("20261019T080000Z-bbbbbb", "ash")
        self.record_order(
            OrderParked(project=None, kind="study", order="trees", run=RUN_ID, step="collect", reason="quota")
        )

        # Act
        ran = run_study(self.runtime, SCAN, self.equipment, None)

        # Assert
        self.assertEqual(ran, {"study": "trees", "run": RUN_ID, "state": "done"})


class RunStudyStartTest(RunStudyArrangement, unittest.TestCase):
    def setUp(self):
        super().setUp()
        token = mock.patch("secrets.token_hex", return_value="c0ffee")
        token.start()
        self.addCleanup(token.stop)

    def test_should_start_a_new_run_after_a_run_done(self):
        # Arrange
        self.record_order(OrderDone(project=None, kind="study", order="trees", run=RUN_ID))

        # Act
        ran = run_study(self.runtime, SCAN, self.equipment, None)

        # Assert
        self.assertEqual(ran, {"study": "trees", "run": "20261019T090000Z-c0ffee", "state": "done"})


class RunStudyParkingTest(RunStudyArrangement, unittest.TestCase):
    def test_should_park_the_run_at_the_step_that_failed(self):
        # Act
        ran = run_study(self.runtime, SCAN_OF_A_MISSING_COLLECTOR, self.equipment, RUN_ID)

        # Assert
        self.assertEqual(
            ran,
            {"study": "trees", "run": RUN_ID, "state": "parked", "step": "collect", "reason": "no collector weather"},
        )

    def test_should_record_the_failed_step_and_the_order_parked(self):
        # Act
        run_study(self.runtime, SCAN_OF_A_MISSING_COLLECTOR, self.equipment, RUN_ID)

        # Assert
        self.assertEqual(
            read_ledger(self.root / "state").entries,
            (
                LedgerEntry(
                    instant=RUNTIME_NOW,
                    event=StepFailed(kind="study", run=RUN_ID, step="collect", reason="no collector weather"),
                ),
                LedgerEntry(
                    instant=RUNTIME_NOW,
                    event=OrderParked(
                        project=None,
                        kind="study",
                        order="trees",
                        run=RUN_ID,
                        step="collect",
                        reason="no collector weather",
                    ),
                ),
            ),
        )

    def test_should_refuse_a_study_whose_run_is_alive(self):
        # Arrange
        self.create_live_run(RUN_ID, "trees")

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            run_study(self.runtime, SCAN, self.equipment, None)

        # Assert
        self.assertEqual(str(refusal.exception), f"@STUDY.trees is running in run {RUN_ID}")

    def test_should_refuse_a_study_whose_output_is_the_inbox(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            run_study(self.runtime, SCAN_INTO_THE_INBOX, self.equipment, RUN_ID)

        # Assert
        self.assertEqual(str(refusal.exception), "the output inbox is refused: the inbox has no store until @TASK.B22")
