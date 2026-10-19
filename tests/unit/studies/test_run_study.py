import json
import os
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.errors import BrigadeError
from brigade.ledger.append_event import append_event
from brigade.ledger.order_done import OrderDone
from brigade.ledger.order_parked import OrderParked
from brigade.ledger.read_ledger import read_ledger
from brigade.runs.record_run_pid import record_run_pid
from brigade.studies.convert_study import Study
from brigade.studies.run_study import run_study
from brigade.studies.study_run_context import StudyEquipment
from brigade.system.read_configuration import Configuration
from tests.unit.create_scripted_runtime import create_scripted_runtime
from tests.unit.scripted_processes import ScriptedProcesses

RUN_ID = "20261019T090000Z-aaaaaa"
ANSWER = 'FINDING trees_20261019T090000Z_aaaaaa\n\tSTUDY "trees"\n\tRUN "20261019T090000Z-aaaaaa"\n'


def create_study(collectors: tuple[str, ...] = (), output: str = "entity:FINDING") -> Study:
    return Study(
        name="trees",
        project=None,
        question=None,
        collectors=collectors,
        slot="none",
        every=None,
        output=output,
        answer_type="FINDING",
        status="active",
    )


def refuse_collector(name: str, project: Path):
    raise BrigadeError(f"no collector {name}")


def refuse_forge(name: str):
    raise AssertionError(f"the study resolved the forge {name}")


def refuse_launch(request, runtime):
    raise AssertionError("the scan launched a judging run")


EQUIPMENT = StudyEquipment(
    collector_equipment=CollectorEquipment(configuration=Configuration(), forge=None, forge_name="github"),
    resolve_collector=refuse_collector,
    document=None,
    resolve_forge=refuse_forge,
    launch_run=refuse_launch,
)


class RunStudyFixture(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.processes = ScriptedProcesses()
        self.runtime = create_scripted_runtime(self.root, self.processes)
        self.config_root = self.runtime.paths.config_root
        self.processes.answer_corpus_change(
            self.config_root, ("findings.awawa",), "brigade study run: the answer of @STUDY.trees"
        )

    def read_events(self) -> list[tuple[str, dict]]:
        return [(entry.event.name, entry.event.to_document()) for entry in read_ledger(self.root / "state").entries]

    def record_order(self, event) -> None:
        append_event(self.runtime.paths, datetime(2026, 10, 18, 7, 0, tzinfo=UTC), event)


class RunStudyTest(RunStudyFixture):
    def test_should_collect_judge_and_write_the_answer_of_the_study(self):
        # Act
        ran = run_study(self.runtime, create_study(), EQUIPMENT, RUN_ID)

        # Assert
        self.assertEqual(
            (ran, (self.config_root / "findings.awawa").read_text(encoding="utf-8")),
            ({"study": "trees", "run": RUN_ID, "state": "done"}, ANSWER),
        )

    def test_should_record_each_step_and_the_order_done(self):
        # Act
        run_study(self.runtime, create_study(), EQUIPMENT, RUN_ID)

        # Assert
        self.assertEqual(
            self.read_events(),
            [
                ("step.done", {"kind": "study", "run": RUN_ID, "step": "collect"}),
                ("step.done", {"kind": "study", "run": RUN_ID, "step": "judge"}),
                ("step.done", {"kind": "study", "run": RUN_ID, "step": "output"}),
                ("order.done", {"project": None, "kind": "study", "order": "trees", "run": RUN_ID}),
            ],
        )

    def test_should_resume_a_run_past_the_steps_it_completed(self):
        # Arrange
        steps = self.root / "state" / "runs" / RUN_ID / "steps"
        steps.mkdir(parents=True)
        (steps / "collect.json").write_text(json.dumps({"collected": []}), encoding="utf-8")

        # Act
        ran = run_study(self.runtime, create_study(("weather",)), EQUIPMENT, RUN_ID)

        # Assert
        self.assertEqual(ran, {"study": "trees", "run": RUN_ID, "state": "done"})

    def test_should_resume_the_parked_run_of_the_study(self):
        # Arrange
        self.record_order(
            OrderParked(project=None, kind="study", order="trees", run=RUN_ID, step="collect", reason="quota")
        )
        self.record_order(OrderDone(project=None, kind="study", order="ash", run="20261018T070000Z-bbbbbb"))

        # Act
        ran = run_study(self.runtime, create_study(), EQUIPMENT, None)

        # Assert
        self.assertEqual(ran["run"], RUN_ID)

    def test_should_start_a_new_run_after_a_run_done(self):
        # Arrange
        self.record_order(OrderDone(project=None, kind="study", order="trees", run=RUN_ID))

        # Act
        ran = run_study(self.runtime, create_study(), EQUIPMENT, None)

        # Assert
        self.assertRegex(ran["run"], r"^20261019T090000Z-[0-9a-f]{6}$")


class RunStudyParkingTest(RunStudyFixture):
    def test_should_park_the_run_at_the_step_that_failed(self):
        # Act
        ran = run_study(self.runtime, create_study(("weather",)), EQUIPMENT, RUN_ID)

        # Assert
        self.assertEqual(
            ran,
            {"study": "trees", "run": RUN_ID, "state": "parked", "step": "collect", "reason": "no collector weather"},
        )

    def test_should_record_the_failed_step_and_the_order_parked(self):
        # Act
        run_study(self.runtime, create_study(("weather",)), EQUIPMENT, RUN_ID)

        # Assert
        self.assertEqual(
            self.read_events(),
            [
                ("step.failed", {"kind": "study", "run": RUN_ID, "step": "collect", "reason": "no collector weather"}),
                (
                    "order.parked",
                    {
                        "project": None,
                        "kind": "study",
                        "order": "trees",
                        "run": RUN_ID,
                        "step": "collect",
                        "reason": "no collector weather",
                    },
                ),
            ],
        )

    def test_should_refuse_a_study_whose_run_is_alive(self):
        # Arrange
        run_directory = self.root / "state" / "runs" / RUN_ID
        run_directory.mkdir(parents=True)
        (run_directory / "study.json").write_text('{"study": "trees"}', encoding="utf-8")
        record_run_pid(run_directory, os.getpid())

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            run_study(self.runtime, create_study(), EQUIPMENT, None)

        # Assert
        self.assertEqual(str(refusal.exception), f"@STUDY.trees is running in run {RUN_ID}")

    def test_should_run_a_study_while_another_study_runs(self):
        # Arrange
        run_directory = self.root / "state" / "runs" / "20261019T080000Z-bbbbbb"
        run_directory.mkdir(parents=True)
        (run_directory / "study.json").write_text('{"study": "ash"}', encoding="utf-8")
        record_run_pid(run_directory, os.getpid())
        self.record_order(
            OrderParked(project=None, kind="study", order="trees", run=RUN_ID, step="collect", reason="quota")
        )

        # Act
        ran = run_study(self.runtime, create_study(), EQUIPMENT, None)

        # Assert
        self.assertEqual(ran, {"study": "trees", "run": RUN_ID, "state": "done"})

    def test_should_refuse_a_study_whose_output_is_the_inbox(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            run_study(self.runtime, create_study(output="inbox"), EQUIPMENT, RUN_ID)

        # Assert
        self.assertEqual(str(refusal.exception), "the output inbox is refused: the inbox has no store until @TASK.B22")
