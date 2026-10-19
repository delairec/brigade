import tempfile
import unittest
from pathlib import Path

from brigade.studies.convert_study import Study
from brigade.studies.read_studies import read_studies
from tests.unit.create_scripted_runtime import create_scripted_runtime
from tests.unit.scripted_processes import ScriptedProcesses


class ReadStudiesTest(unittest.TestCase):
    def test_should_read_every_study_of_the_operational_corpus(self):
        # Arrange
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        processes = ScriptedProcesses()
        runtime = create_scripted_runtime(Path(directory.name), processes)
        processes.answer_entities(
            runtime.paths.config_root,
            "STUDY",
            {"trees": (("SLOT", "none"), ("OUTPUT", "entity:FINDING"), ("ANSWER", "FINDING"), ("STATUS", "active"))},
        )

        # Act
        studies = read_studies(runtime)

        # Assert
        self.assertEqual(
            studies,
            (
                Study(
                    name="trees",
                    project=None,
                    question=None,
                    collectors=(),
                    slot="none",
                    every=None,
                    output="entity:FINDING",
                    answer_type="FINDING",
                    status="active",
                ),
            ),
        )
