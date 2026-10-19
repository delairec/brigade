import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.studies.change_study_status import change_study_status
from tests.unit.create_scripted_runtime import create_scripted_runtime
from tests.unit.scripted_processes import ScriptedProcesses

STUDIES = "STUDY trees\n\tSLOT none\n\tSTATUS active\n"
ACTIVE_STUDY = (("SLOT", "none"), ("OUTPUT", "entity:FINDING"), ("ANSWER", "FINDING"), ("STATUS", "active"))
ARCHIVED_STUDY = (("SLOT", "none"), ("OUTPUT", "entity:FINDING"), ("ANSWER", "FINDING"), ("STATUS", "archived"))


class ChangeStudyStatusTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.processes = ScriptedProcesses()
        self.runtime = create_scripted_runtime(Path(directory.name), self.processes)
        self.config_root = self.runtime.paths.config_root
        self.studies = self.config_root / "studies.awawa"
        self.studies.write_text(STUDIES, encoding="utf-8")

    def script_pause(self) -> None:
        self.processes.answer_entity(self.config_root, "STUDY", "trees", ACTIVE_STUDY)
        self.processes.answer_corpus_change(self.config_root, ("studies.awawa",), "brigade study pause: trees")

    def test_should_report_the_pause_of_an_active_study(self):
        # Arrange
        self.script_pause()

        # Act
        changed = change_study_status(self.runtime, "trees", "paused")

        # Assert
        self.assertEqual(changed, {"schema_version": 1, "study": "trees", "status": "paused", "changed": True})

    def test_should_write_the_pause_of_an_active_study_in_the_studies_file(self):
        # Arrange
        self.script_pause()

        # Act
        change_study_status(self.runtime, "trees", "paused")

        # Assert
        self.assertEqual(self.studies.read_text(encoding="utf-8"), "STUDY trees\n\tSLOT none\n\tSTATUS paused\n")

    def test_should_change_nothing_for_a_study_already_in_the_status(self):
        # Arrange
        self.processes.answer_entity(self.config_root, "STUDY", "trees", ACTIVE_STUDY)

        # Act
        changed = change_study_status(self.runtime, "trees", "active")

        # Assert
        self.assertEqual(changed, {"schema_version": 1, "study": "trees", "status": "active", "changed": False})

    def test_should_refuse_to_pause_or_resume_an_archived_study(self):
        # Arrange
        self.processes.answer_entity(self.config_root, "STUDY", "trees", ARCHIVED_STUDY)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            change_study_status(self.runtime, "trees", "active")

        # Assert
        self.assertEqual(str(refusal.exception), "@STUDY.trees is archived; it is neither paused nor resumed")

    def test_should_refuse_a_study_written_elsewhere_than_the_studies_file(self):
        # Arrange
        self.processes.answer_entity(self.config_root, "STUDY", "ash", ACTIVE_STUDY)

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            change_study_status(self.runtime, "ash", "paused")

        # Assert
        self.assertEqual(str(refusal.exception), "@STUDY.ash is not written in studies.awawa")
