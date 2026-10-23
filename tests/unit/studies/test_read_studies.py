import tempfile
import unittest
from pathlib import Path

from brigade.studies.convert_study import Study
from brigade.studies.read_studies import read_studies
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses


class ReadStudiesTest(unittest.TestCase):
    def test_should_read_every_study_of_the_operational_corpus(self):
        # Arrange
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        processes = ScriptedProcesses()
        write_operational_corpus(Path(directory.name))
        runtime = create_test_runtime(create_test_paths(Path(directory.name)), run_process=processes)
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
