import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.studies.change_study_status import change_study_status
from tests.unit.create_scripted_runtime import create_scripted_runtime
from tests.unit.scripted_processes import ScriptedProcesses

STUDIES = "STUDY trees\n\tSLOT none\n\tSTATUS active\n"


def create_study_fields(status: str) -> tuple:
    return (("SLOT", "none"), ("OUTPUT", "entity:FINDING"), ("ANSWER", "FINDING"), ("STATUS", status))


class ChangeStudyStatusTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.processes = ScriptedProcesses()
        self.runtime = create_scripted_runtime(Path(directory.name), self.processes)
        self.config_root = self.runtime.paths.config_root
        self.studies = self.config_root / "studies.awawa"
        self.studies.write_text(STUDIES, encoding="utf-8")

    def test_should_pause_an_active_study(self):
        # Arrange
        self.processes.answer_entity(self.config_root, "STUDY", "trees", create_study_fields("active"))
        self.processes.answer_corpus_change(self.config_root, ("studies.awawa",), "brigade study pause: trees")

        # Act
        changed = change_study_status(self.runtime, "trees", "paused")

        # Assert
        self.assertEqual(
            (changed, self.studies.read_text(encoding="utf-8")),
            (
                {"schema_version": 1, "study": "trees", "status": "paused", "changed": True},
                "STUDY trees\n\tSLOT none\n\tSTATUS paused\n",
            ),
        )

    def test_should_change_nothing_for_a_study_already_in_the_status(self):
        # Arrange
        self.processes.answer_entity(self.config_root, "STUDY", "trees", create_study_fields("active"))

        # Act
        changed = change_study_status(self.runtime, "trees", "active")

        # Assert
        self.assertEqual(changed, {"schema_version": 1, "study": "trees", "status": "active", "changed": False})

    def test_should_refuse_to_pause_or_resume_an_archived_study(self):
        # Arrange
        self.processes.answer_entity(self.config_root, "STUDY", "trees", create_study_fields("archived"))

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            change_study_status(self.runtime, "trees", "active")

        # Assert
        self.assertEqual(str(refusal.exception), "@STUDY.trees is archived; it is neither paused nor resumed")

    def test_should_refuse_a_study_written_elsewhere_than_the_studies_file(self):
        # Arrange
        self.processes.answer_entity(self.config_root, "STUDY", "ash", create_study_fields("active"))

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            change_study_status(self.runtime, "ash", "paused")

        # Assert
        self.assertEqual(str(refusal.exception), "@STUDY.ash is not written in studies.awawa")
