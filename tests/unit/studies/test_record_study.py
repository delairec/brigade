import tempfile
import unittest
from pathlib import Path

from brigade.studies.record_study import NewStudy, record_study
from tests.unit.create_scripted_runtime import create_scripted_runtime
from tests.unit.scripted_processes import ScriptedProcesses


class RecordStudyTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.processes = ScriptedProcesses()
        self.runtime = create_scripted_runtime(Path(directory.name), self.processes)
        self.studies = self.runtime.paths.config_root / "studies.awawa"

    def test_should_write_a_study_of_a_project_asking_a_question_on_a_schedule(self):
        # Arrange
        root = self.runtime.paths.config_root
        self.processes.answer_corpus_change(root, ("studies.awawa",), "brigade study new: @STUDY.trees")
        study = NewStudy(
            name="trees",
            title="The trees",
            question="how many trees?",
            project="oak",
            collectors=("git-log", "shell: ls"),
            slot="review",
            every="daily@07:00",
            output="issue",
            answer_type="FINDING",
        )

        # Act
        record_study(self.runtime, study)

        # Assert
        self.assertEqual(
            self.studies.read_text(encoding="utf-8"),
            "STUDY trees\n"
            '\tTITLE "The trees"\n'
            '\tQUESTION "how many trees?"\n'
            "\tPROJECT @PROJECT.oak\n"
            '\tCOLLECTOR "git-log"\n'
            '\tCOLLECTOR "shell: ls"\n'
            "\tSLOT review\n"
            '\tEVERY "daily@07:00"\n'
            '\tOUTPUT "issue"\n'
            '\tANSWER "FINDING"\n'
            "\tSTATUS active\n",
        )

    def test_should_append_a_scan_of_no_project_run_on_demand_after_the_recorded_studies(self):
        # Arrange
        self.studies.write_text("STUDY trees\n\tSTATUS active\n", encoding="utf-8")
        root = self.runtime.paths.config_root
        self.processes.answer_corpus_change(root, ("studies.awawa",), "brigade study new: @STUDY.scan")
        study = NewStudy(
            name="scan",
            title="The scan",
            question=None,
            project=None,
            collectors=(),
            slot="none",
            every=None,
            output="entity:FINDING",
            answer_type="FINDING",
        )

        # Act
        record_study(self.runtime, study)

        # Assert
        self.assertEqual(
            self.studies.read_text(encoding="utf-8"),
            "STUDY trees\n"
            "\tSTATUS active\n"
            "\n"
            "STUDY scan\n"
            '\tTITLE "The scan"\n'
            "\tSLOT none\n"
            '\tOUTPUT "entity:FINDING"\n'
            '\tANSWER "FINDING"\n'
            "\tSTATUS active\n",
        )
