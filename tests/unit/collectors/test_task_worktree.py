import json
import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.collecting.collector_equipment import CollectorEquipment
from brigade.collectors.task_worktree import collect
from brigade.system.parse_configuration import Configuration
from tests.unit.create_recipe_answers import create_recipe_answers
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.recording_process_runner import RecordingProcessRunner
from tests.unit.registry_answers import create_registry_answers

WORKTREE = Path("/srv/oak-b12")
NO_FORGE_EQUIPMENT = CollectorEquipment(
    configuration=Configuration(), forge=None, forge_name="none", resolve_client=None
)


class TaskWorktreeCollectorTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        self.paths = create_test_paths(self.root)
        self.paths.config_root.mkdir(parents=True)
        self.paths.schema_file.write_text("SCHEMA PROJECT\n")

    def collect_from(self, project: dict, corpus: Path) -> dict:
        runner = RecordingProcessRunner(
            {
                **create_registry_answers(self.paths.config_root, {"oak": project}),
                **create_recipe_answers(corpus, {"acceptance": (("python3", "-m", "unittest"),)}),
            }
        )
        environment = {
            "BRIGADE_PROJECT_PATH": "/srv/oak",
            "BRIGADE_SINCE": "1970-01-01",
            "BRIGADE_PARAMS": json.dumps({"worktree": str(WORKTREE)}),
        }
        return collect(environment, create_test_runtime(self.paths, run_process=runner), NO_FORGE_EQUIPMENT)

    def test_should_name_the_worktree_as_the_checkout_and_the_corpus_and_its_acceptance_commands(self):
        # Act
        document = self.collect_from({"PATH": "/srv/oak", "FORGE": "none"}, WORKTREE)

        # Assert
        self.assertEqual(
            document["summary"],
            {"checkout": "/srv/oak-b12", "head_tree": "/srv/oak-b12", "acceptance": [["python3", "-m", "unittest"]]},
        )

    def test_should_name_the_area_of_the_corpus_in_the_worktree_of_a_project_in_mode_area(self):
        # Arrange
        corpus_area = WORKTREE / "spec"

        # Act
        document = self.collect_from({"PATH": "/srv/oak", "MODE": "area", "CORPUS": "spec"}, corpus_area)

        # Assert
        self.assertEqual(document["summary"]["head_tree"], "/srv/oak-b12/spec")

    def test_should_collect_afresh_at_each_call(self):
        # Act
        document = self.collect_from({"PATH": "/srv/oak", "FORGE": "none"}, WORKTREE)

        # Assert
        self.assertFalse(document["cache"])
