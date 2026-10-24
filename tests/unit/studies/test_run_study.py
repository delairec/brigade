import dataclasses
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.ledger.append_event import append_event
from brigade.ledger.ledger_entry import LedgerEntry
from brigade.ledger.order_done import OrderDone
from brigade.ledger.order_parked import OrderParked
from brigade.ledger.read_ledger import read_ledger
from brigade.ledger.step_done import StepDone
from brigade.ledger.step_failed import StepFailed
from brigade.studies.convert_study import Study
from brigade.studies.run_study import run_study
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import FIXED_NOW, create_test_runtime
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
JUDGED_STUDY = Study(
    name="trees",
    project=None,
    question="are the trees healthy?",
    collectors=(),
    slot="report",
    every=None,
    output="entity:FINDING",
    answer_type="FINDING",
    status="active",
)
RECORDED_ANSWER = 'FINDING trees_20261019T090000Z_aaaaaa\n\tVERDICT "healthy"\n'


def refuse_collector(name: str, project: Path):
    raise BrigadeError(f"no collector {name}")


class RunStudyTestCase(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.processes = ScriptedProcesses()
        write_operational_corpus(self.root)
        self.runtime = create_test_runtime(create_test_paths(self.root), run_process=self.processes)
        self.live_run_directories = set()
        self.held_run_directories = []
        self.equipment = create_study_equipment(
            resolve_collector=refuse_collector,
            name_run={FIXED_NOW: "20261019T090000Z-c0ffee"}.__getitem__,
            is_run_alive=self.live_run_directories.__contains__,
            record_own_pid=self.held_run_directories.append,
        )
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
        self.live_run_directories.add(run_directory)


class RunStudyTest(RunStudyTestCase):
    def test_should_answer_the_run_done(self):
        # Act
        ran = run_study(self.runtime, SCAN, self.equipment, RUN_ID)

        # Assert
        self.assertEqual(ran, {"study": "trees", "run": RUN_ID, "state": "done"})

    def test_should_hold_the_run_by_the_process_of_brigade(self):
        # Act
        run_study(self.runtime, SCAN, self.equipment, RUN_ID)

        # Assert
        self.assertEqual(self.held_run_directories, [self.root / "state" / "runs" / RUN_ID])

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
                LedgerEntry(instant=FIXED_NOW, event=StepDone(kind="study", run=RUN_ID, step="collect")),
                LedgerEntry(instant=FIXED_NOW, event=StepDone(kind="study", run=RUN_ID, step="judge")),
                LedgerEntry(instant=FIXED_NOW, event=StepDone(kind="study", run=RUN_ID, step="output")),
                LedgerEntry(instant=FIXED_NOW, event=OrderDone(project=None, kind="study", order="trees", run=RUN_ID)),
            ),
        )

    def test_should_write_the_result_of_each_step_under_the_run_directory(self):
        # Arrange
        steps = self.root / "state" / "runs" / RUN_ID / "steps"

        # Act
        run_study(self.runtime, SCAN, self.equipment, RUN_ID)

        # Assert
        self.assertEqual(sorted(steps.iterdir()), [steps / "collect.json", steps / "judge.json", steps / "output.json"])

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


class RunStudyStartTest(RunStudyTestCase):
    def test_should_start_a_new_run_after_a_run_done(self):
        # Arrange
        self.record_order(OrderDone(project=None, kind="study", order="trees", run=RUN_ID))

        # Act
        ran = run_study(self.runtime, SCAN, self.equipment, None)

        # Assert
        self.assertEqual(ran, {"study": "trees", "run": "20261019T090000Z-c0ffee", "state": "done"})


class RunStudyParkingTest(RunStudyTestCase):
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
                    instant=FIXED_NOW,
                    event=StepFailed(kind="study", run=RUN_ID, step="collect", reason="no collector weather"),
                ),
                LedgerEntry(
                    instant=FIXED_NOW,
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

    def test_should_start_no_run_of_a_study_whose_run_is_alive(self):
        # Arrange
        self.create_live_run(RUN_ID, "trees")

        # Act
        with self.assertRaises(BrigadeError):
            run_study(self.runtime, SCAN, self.equipment, None)

        # Assert
        self.assertEqual(read_ledger(self.root / "state").entries, ())

    def test_should_start_no_run_of_a_study_whose_output_is_the_inbox(self):
        # Act
        with self.assertRaises(BrigadeError):
            run_study(self.runtime, SCAN_INTO_THE_INBOX, self.equipment, None)

        # Assert
        self.assertEqual(read_ledger(self.root / "state").entries, ())

    def test_should_refuse_a_study_whose_output_is_the_inbox(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            run_study(self.runtime, SCAN_INTO_THE_INBOX, self.equipment, RUN_ID)

        # Assert
        self.assertEqual(str(refusal.exception), "the output inbox is refused: the inbox has no store until @TASK.B22")


class RunStudyParkedAtItsJudgingRunTest(RunStudyTestCase):
    def test_should_finish_the_run_once_its_answer_is_recorded(self):
        # Arrange
        run_directory = self.root / "state" / "runs" / RUN_ID
        (run_directory / "steps").mkdir(parents=True)
        (run_directory / "steps" / "collect.json").write_text('{"collected": []}', encoding="utf-8")
        (run_directory / "answer.awawa").write_text(RECORDED_ANSWER, encoding="utf-8")
        self.record_order(
            OrderParked(
                project=None,
                kind="study",
                order="trees",
                run=RUN_ID,
                step="judge",
                reason="the judging run 20261019T080000Z-dddddd gave no answer",
            )
        )
        equipment = dataclasses.replace(
            self.equipment, launch_run=lambda request, runtime: {"run": "20261019T090500Z-eeeeee"}
        )

        # Act
        ran = run_study(self.runtime, JUDGED_STUDY, equipment, None)

        # Assert
        self.assertEqual(ran, {"study": "trees", "run": RUN_ID, "state": "done"})
        self.assertEqual((self.config_root / "findings.awawa").read_text(encoding="utf-8"), RECORDED_ANSWER)
