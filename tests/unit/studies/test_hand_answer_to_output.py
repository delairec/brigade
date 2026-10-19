import json
import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.studies.convert_study import Study
from brigade.studies.hand_answer_to_output import hand_answer_to_output
from brigade.studies.present_answer import AnswerPublication
from brigade.studies.study_run_context import StudyRunContext
from tests.unit.create_scripted_runtime import create_scripted_runtime
from tests.unit.scripted_processes import ScriptedProcesses

RUN_ID = "20261019T090000Z-aaaaaa"
STUDY = Study(
    name="trees",
    project=None,
    question=None,
    collectors=(),
    slot="none",
    every=None,
    output="slack",
    answer_type="FINDING",
    status="active",
)
PUBLICATION = AnswerPublication(title="Study trees, run 1", markdown="# FINDING trees_1\n")


class HandAnswerToOutputTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.executable = self.bin / "brigade-output-slack"
        self.processes = ScriptedProcesses()
        runtime = create_scripted_runtime(self.root, self.processes, executable_search_path=str(self.bin))
        self.context = StudyRunContext(
            runtime=runtime, study=STUDY, run_id=RUN_ID, run_directory=self.root / "run", equipment=None
        )

    def install_output(self) -> None:
        self.executable.write_text("#!/bin/sh\n", encoding="utf-8")
        self.executable.chmod(0o755)
        self.processes.answer((str(self.executable),))

    def test_should_answer_the_output_executable_found_on_the_search_path(self):
        # Arrange
        self.install_output()

        # Act
        handed = hand_answer_to_output(self.context, PUBLICATION)

        # Assert
        self.assertEqual(handed, {"executable": str(self.executable)})

    def test_should_hand_the_answer_to_the_output_executable_on_its_input(self):
        # Arrange
        self.install_output()

        # Act
        hand_answer_to_output(self.context, PUBLICATION)

        # Assert
        self.assertEqual(
            json.loads(self.processes.requests[0].stdin),
            {"schema_version": 1, "study": "trees", "run": RUN_ID, "markdown": "# FINDING trees_1\n"},
        )

    def test_should_run_the_output_executable_in_the_run_directory(self):
        # Arrange
        self.install_output()

        # Act
        hand_answer_to_output(self.context, PUBLICATION)

        # Assert
        self.assertEqual(self.processes.requests[0].cwd, str(self.root / "run"))

    def test_should_refuse_an_output_no_executable_provides(self):
        # Act
        with self.assertRaises(BrigadeError) as refusal:
            hand_answer_to_output(self.context, PUBLICATION)

        # Assert
        self.assertEqual(str(refusal.exception), "no output slack: no brigade-output-slack on PATH")
