import contextlib
import json
import tempfile
import unittest
from pathlib import Path

from brigade.commands._locate_preflights import locate_preflights
from brigade.preflights.find_preflight import find_preflight
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner
from tests.unit.registry_answers import create_registry_answers

MACHINE_NIGHTLY = (
    'schema_version = 1\nname = "nightly"\ndescription = "the nightly of the machine"\ncollectors = []\nchecks = []\n'
)
PROJECT_NIGHTLY = (
    'schema_version = 1\nname = "nightly"\ndescription = "the nightly of the project"\ncollectors = []\nchecks = []\n'
)
NIGHTLY_ENTITY = {
    "file": "/srv/shop/preflights.awawa",
    "fields": [{"name": "TITLE", "atoms": ['"the nightly of the corpus"'], "fields": []}],
}
NOT_DEFINED = ProcessAnswer(exit_code=1, stderr="awawa show: @PREFLIGHT.nightly is not defined in the workspace\n")


class LocatePreflightsTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        root = Path(self.root.name).resolve()
        self.project = root / "shop"
        self.project.mkdir()
        self.enterContext(contextlib.chdir(self.project))
        self.paths = create_test_paths(root)
        (self.paths.config_root / "preflights").mkdir(parents=True)
        (self.paths.config_root / "preflights" / "nightly.toml").write_text(MACHINE_NIGHTLY)

    def find_nightly(self, mode: str, entity: ProcessAnswer, name: str = "nightly") -> dict:
        runner = RecordingProcessRunner(
            {
                **create_registry_answers(self.paths.config_root, {"shop": {"PATH": str(self.project), "MODE": mode}}),
                ("awawa", "show", "@PREFLIGHT.nightly", "--json", str(self.project)): entity,
            }
        )
        return find_preflight(
            name, locate_preflights(self.project, create_test_runtime(self.paths, run_process=runner))
        )

    def test_should_read_the_preflight_of_a_project_with_a_corpus_from_its_preflight_entity(self):
        # Act
        preflight = self.find_nightly("control", ProcessAnswer(stdout=json.dumps(NIGHTLY_ENTITY)))

        # Assert
        self.assertEqual(preflight["description"], "the nightly of the corpus")

    def test_should_read_the_preflight_of_a_project_without_a_corpus_from_its_brigade_preflights(self):
        # Arrange
        (self.project / ".brigade" / "preflights").mkdir(parents=True)
        (self.project / ".brigade" / "preflights" / "nightly.toml").write_text(PROJECT_NIGHTLY)

        # Act
        preflight = self.find_nightly("none", NOT_DEFINED)

        # Assert
        self.assertEqual(preflight["description"], "the nightly of the project")

    def test_should_read_the_preflight_of_the_machine_where_the_project_holds_none(self):
        # Act
        preflight = self.find_nightly("control", NOT_DEFINED)

        # Assert
        self.assertEqual(preflight["description"], "the nightly of the machine")

    def test_should_read_a_built_in_preflight_where_neither_the_project_nor_the_machine_holds_it(self):
        # Act
        preflight = self.find_nightly("none", NOT_DEFINED, name="review-pull-request")

        # Assert
        self.assertEqual(
            preflight["description"], "the deterministic checks of the pull request of a task, before any judgment"
        )
