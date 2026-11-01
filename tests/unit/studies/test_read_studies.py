import tempfile
import unittest
from pathlib import Path

from brigade.studies.convert_study import Study
from brigade.studies.read_studies import read_studies
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses
from tests.unit.studies.built_in_triage import BUILT_IN_TRIAGE
from tests.unit.studies.scans_of_oak import SCANS_OF_OAK


class ReadStudiesTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.processes = ScriptedProcesses()
        write_operational_corpus(Path(directory.name))
        self.runtime = create_test_runtime(create_test_paths(Path(directory.name)), run_process=self.processes)

    def test_should_read_every_study_of_the_operational_corpus_then_the_built_in_triage(self):
        # Arrange
        self.processes.answer_entities(self.runtime.paths.config_root, "PROJECT", {})
        self.processes.answer_entities(
            self.runtime.paths.config_root,
            "STUDY",
            {"trees": (("SLOT", "none"), ("OUTPUT", "entity:FINDING"), ("ANSWER", "FINDING"), ("STATUS", "active"))},
        )

        # Act
        studies = read_studies(self.runtime)

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
                BUILT_IN_TRIAGE,
            ),
        )

    def test_should_list_the_built_in_scans_of_each_registered_project(self):
        # Arrange
        no_recorded_study = {}
        self.processes.answer_entities(self.runtime.paths.config_root, "STUDY", no_recorded_study)
        self.processes.answer_entities(self.runtime.paths.config_root, "PROJECT", {"oak": (("PATH", "/srv/oak"),)})

        # Act
        studies = read_studies(self.runtime)

        # Assert
        self.assertEqual(studies, (BUILT_IN_TRIAGE, *SCANS_OF_OAK))

    def test_should_take_the_triage_the_operational_corpus_defines_over_the_built_in_one(self):
        # Arrange
        self.processes.answer_entities(self.runtime.paths.config_root, "PROJECT", {})
        self.processes.answer_entities(
            self.runtime.paths.config_root,
            "STUDY",
            {
                "triage": (
                    ("COLLECTOR", "inbox-families"),
                    ("SLOT", "triage"),
                    ("EVERY", "mon@07:00"),
                    ("OUTPUT", "entity:PATTERN"),
                    ("ANSWER", "PATTERN"),
                    ("STATUS", "paused"),
                )
            },
        )

        # Act
        studies = read_studies(self.runtime)

        # Assert
        self.assertEqual(
            studies,
            (
                Study(
                    name="triage",
                    project=None,
                    question=None,
                    collectors=("inbox-families",),
                    slot="triage",
                    every="mon@07:00",
                    output="entity:PATTERN",
                    answer_type="PATTERN",
                    status="paused",
                ),
            ),
        )
