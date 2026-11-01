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
from tests.unit.studies.built_in_triage import BUILT_IN_TRIAGE
from tests.unit.studies.scans_of_oak import SCANS_OF_OAK


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
        self.processes.answer_entities(self.runtime.paths.config_root, "PROJECT", {"oak": (("PATH", "/srv/oak"),)})
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

    def test_should_read_the_built_in_triage_the_operational_corpus_does_not_define(self):
        # Arrange
        self.processes.answer_entities(self.runtime.paths.config_root, "PROJECT", {})
        self.processes.answer(
            ("awawa", "show", "@STUDY.triage", "--json", str(self.runtime.paths.config_root)),
            exit_code=1,
            stderr="awawa show: @STUDY.triage is not defined in the workspace\n",
        )

        # Act
        study = read_study(self.runtime, "triage")

        # Assert
        self.assertEqual(study, BUILT_IN_TRIAGE)

    def test_should_take_the_triage_the_operational_corpus_defines_over_the_built_in_one(self):
        # Arrange
        self.processes.answer_entity(
            self.runtime.paths.config_root,
            "STUDY",
            "triage",
            (("SLOT", "triage"), ("OUTPUT", "entity:PATTERN"), ("ANSWER", "PATTERN"), ("STATUS", "paused")),
        )

        # Act
        study = read_study(self.runtime, "triage")

        # Assert
        self.assertEqual(
            study,
            Study(
                name="triage",
                project=None,
                question=None,
                collectors=(),
                slot="triage",
                every=None,
                output="entity:PATTERN",
                answer_type="PATTERN",
                status="paused",
            ),
        )

    def test_should_read_the_built_in_scan_of_a_registered_project_the_operational_corpus_does_not_define(self):
        # Arrange
        self.processes.answer_entities(self.runtime.paths.config_root, "PROJECT", {"oak": (("PATH", "/srv/oak"),)})
        self.processes.answer(
            ("awawa", "show", "@STUDY.corpus_lint_oak", "--json", str(self.runtime.paths.config_root)),
            exit_code=1,
            stderr="awawa show: @STUDY.corpus_lint_oak is not defined in the workspace\n",
        )

        # Act
        study = read_study(self.runtime, "corpus_lint_oak")

        # Assert
        self.assertEqual(study, SCANS_OF_OAK[0])

    def test_should_take_the_scan_the_operational_corpus_defines_over_the_built_in_one(self):
        # Arrange
        self.processes.answer_entity(
            self.runtime.paths.config_root,
            "STUDY",
            "corpus_lint_oak",
            (("SLOT", "none"), ("OUTPUT", "inbox"), ("ANSWER", "ANSWER"), ("STATUS", "paused")),
        )

        # Act
        study = read_study(self.runtime, "corpus_lint_oak")

        # Assert
        self.assertEqual(
            study,
            Study(
                name="corpus_lint_oak",
                project=None,
                question=None,
                collectors=(),
                slot="none",
                every=None,
                output="inbox",
                answer_type="ANSWER",
                status="paused",
            ),
        )


class ReadStudyWithoutOperationalCorpusTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.processes = ScriptedProcesses()
        self.runtime = create_test_runtime(create_test_paths(Path(directory.name)), run_process=self.processes)

    def test_should_refuse_the_built_in_triage_on_a_machine_without_an_operational_corpus(self):
        # Arrange
        self.processes.answer(
            ("awawa", "show", "@STUDY.triage", "--json", str(self.runtime.paths.config_root)),
            exit_code=1,
            stderr="awawa show: @STUDY.triage is not defined in the workspace\n",
        )

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            read_study(self.runtime, "triage")

        # Assert
        self.assertEqual(str(refusal.exception), "the operational corpus is missing; run brigade init first")
