import tempfile
import unittest
from pathlib import Path

from brigade.studies.list_built_in_studies import list_built_in_studies
from tests.unit.commands.command_runtime import write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.scripted_processes import ScriptedProcesses
from tests.unit.studies.built_in_triage import BUILT_IN_TRIAGE
from tests.unit.studies.scans_of_oak import SCANS_OF_OAK


class ListBuiltInStudiesTest(unittest.TestCase):
    def test_should_list_the_triage_then_the_scans_of_each_registered_project(self):
        # Arrange
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        processes = ScriptedProcesses()
        write_operational_corpus(Path(directory.name))
        runtime = create_test_runtime(create_test_paths(Path(directory.name)), run_process=processes)
        processes.answer_entities(runtime.paths.config_root, "PROJECT", {"oak": (("PATH", "/srv/oak"),)})

        # Act
        studies = list_built_in_studies(runtime)

        # Assert
        self.assertEqual(studies, (BUILT_IN_TRIAGE, *SCANS_OF_OAK))
