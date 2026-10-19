import argparse
import tempfile
import unittest
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.errors import BrigadeError
from brigade.studies.convert_study import Study
from brigade.studies.judge_evidence import judge_evidence
from brigade.studies.study_run_context import StudyEquipment, StudyRunContext
from brigade.system.read_configuration import Configuration
from tests.unit.create_scripted_runtime import create_scripted_runtime
from tests.unit.scripted_processes import ScriptedProcesses

RUN_ID = "20261019T090000Z-aaaaaa"


def create_study(slot: str) -> Study:
    return Study(
        name="trees",
        project="oak",
        question="how many trees?",
        collectors=(),
        slot=slot,
        every=None,
        output="entity:FINDING",
        answer_type="FINDING",
        status="active",
    )


def refuse_collector(name: str, project: Path):
    raise AssertionError(f"the judging resolved the collector {name}")


def refuse_forge(name: str):
    raise AssertionError(f"the judging resolved the forge {name}")


class RunLauncherDouble:
    def __init__(self, run_directory: Path, *, answers: bool):
        self.requests = []
        self._answer_file = run_directory / "answer.awawa"
        self._answers = answers

    def launch(self, request, runtime) -> dict:
        self.requests.append(request)
        if self._answers:
            self._answer_file.write_text("FINDING trees_1\n", encoding="utf-8")
        return {"run": "20261019T090100Z-bbbbbb"}


class JudgeEvidenceTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.runtime = create_scripted_runtime(self.root, ScriptedProcesses())
        self.run_directory = self.root / "state" / "runs" / RUN_ID
        self.run_directory.mkdir(parents=True)

    def create_context(self, slot: str, launcher: RunLauncherDouble) -> StudyRunContext:
        equipment = StudyEquipment(
            collector_equipment=CollectorEquipment(configuration=Configuration(), forge=None, forge_name="github"),
            resolve_collector=refuse_collector,
            document=None,
            resolve_forge=refuse_forge,
            launch_run=launcher.launch,
        )
        return StudyRunContext(
            runtime=self.runtime,
            study=create_study(slot),
            run_id=RUN_ID,
            run_directory=self.run_directory,
            equipment=equipment,
        )

    def test_should_answer_the_judging_run(self):
        # Arrange
        launcher = RunLauncherDouble(self.run_directory, answers=True)

        # Act
        judged = judge_evidence(self.create_context("review", launcher))

        # Assert
        self.assertEqual(judged, {"run": "20261019T090100Z-bbbbbb"})

    def test_should_launch_the_study_procedure_in_the_slot_of_the_study(self):
        # Arrange
        launcher = RunLauncherDouble(self.run_directory, answers=True)

        # Act
        judge_evidence(self.create_context("review", launcher))

        # Assert
        self.assertEqual(
            launcher.requests,
            [
                argparse.Namespace(
                    procedure="study",
                    slot="review",
                    project="oak",
                    cwd=None,
                    brief=None,
                    arguments=("study=trees", f"run={RUN_ID}"),
                    run_id=None,
                    wave=None,
                    task=None,
                    detach=False,
                    resume=False,
                )
            ],
        )

    def test_should_refuse_a_judging_run_that_gave_no_answer(self):
        # Arrange
        launcher = RunLauncherDouble(self.run_directory, answers=False)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            judge_evidence(self.create_context("review", launcher))

        # Assert
        self.assertEqual(str(refusal.exception), "the judging run 20261019T090100Z-bbbbbb gave no answer")

    def test_should_judge_nothing_for_a_scan(self):
        # Arrange
        launcher = RunLauncherDouble(self.run_directory, answers=True)

        # Act
        judged = judge_evidence(self.create_context("none", launcher))

        # Assert
        self.assertEqual(judged, {"run": None})

    def test_should_launch_no_run_for_a_scan(self):
        # Arrange
        launcher = RunLauncherDouble(self.run_directory, answers=True)

        # Act
        judge_evidence(self.create_context("none", launcher))

        # Assert
        self.assertEqual(launcher.requests, [])
