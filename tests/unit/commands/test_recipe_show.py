import argparse
import contextlib
import tempfile
import unittest
from pathlib import Path

from brigade.commands.recipe_show import COMMAND, recipe_show
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.recipes.recipe_files import write_recipe
from tests.unit.recording_process_runner import RecordingProcessRunner
from tests.unit.registry_answers import create_registry_answers

NO_PROJECT_REGISTERED = {}


class RecipeShowTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        root = Path(self.root.name).resolve()
        paths = create_test_paths(root)
        write_recipe(paths.config_root / "recipes", "nightly", "the machine's nightly")
        (root / "shop").mkdir()
        self.enterContext(contextlib.chdir(root / "shop"))
        runner = RecordingProcessRunner(create_registry_answers(paths.config_root, NO_PROJECT_REGISTERED))
        self.runtime = create_test_runtime(paths, run_process=runner)

    def test_should_show_the_recipe_resolved_and_its_source(self):
        # Act
        document = recipe_show(argparse.Namespace(name="nightly"), self.runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "source": "machine",
                "recipe": {
                    "schema_version": 1,
                    "name": "nightly",
                    "description": "the machine's nightly",
                    "params": [],
                    "max_wall": 5,
                    "steps": [],
                },
            },
        )

    def test_should_print_the_source_then_the_recipe(self):
        # Arrange
        document = {"schema_version": 1, "source": "machine", "recipe": {"name": "nightly", "steps": []}}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, 'source machine\n{\n  "name": "nightly",\n  "steps": []\n}')
