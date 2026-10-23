import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.studies.convert_study import Study
from brigade.studies.read_study import read_study
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses


class ReadStudyTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.processes = ScriptedProcesses()
        write_operational_corpus(Path(directory.name))
        self.runtime = create_test_runtime(create_test_paths(Path(directory.name)), run_process=self.processes)

    def test_should_read_the_named_study_of_the_operational_corpus(self):
        # Arrange
        self.processes.answer_entity(
            self.runtime.paths.config_root,
            "STUDY",
            "trees",
            (("SLOT", "none"), ("OUTPUT", "entity:FINDING"), ("ANSWER", "FINDING"), ("STATUS", "active")),
        )

        # Act
        study = read_study(self.runtime, "trees")

        # Assert
        self.assertEqual(
            study,
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
        )

    def test_should_refuse_a_study_the_operational_corpus_does_not_define(self):
        # Arrange
        self.processes.answer(
            ("awawa", "show", "@STUDY.ash", "--json", str(self.runtime.paths.config_root)),
            exit_code=1,
            stderr="awawa show: @STUDY.ash is not defined in the workspace\n",
        )

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            read_study(self.runtime, "ash")

        # Assert
        self.assertEqual(str(refusal.exception), "@STUDY.ash is not defined in the operational corpus")
