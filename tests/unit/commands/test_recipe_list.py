import argparse
import contextlib
import tempfile
import unittest
from pathlib import Path

from brigade.commands.recipe_list import COMMAND, recipe_list
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.recipes.recipe_files import write_recipe
from tests.unit.recording_process_runner import RecordingProcessRunner
from tests.unit.registry_answers import create_registry_answers

NO_PROJECT_REGISTERED = {}


class RecipeListTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        root = Path(self.root.name).resolve()
        paths = create_test_paths(root)
        write_recipe(root / "shop" / ".brigade" / "recipes", "review", "the project's review")
        write_recipe(paths.config_root / "recipes", "nightly", "the machine's nightly")
        self.enterContext(contextlib.chdir(root / "shop"))
        runner = RecordingProcessRunner(create_registry_answers(paths.config_root, NO_PROJECT_REGISTERED))
        self.runtime = create_test_runtime(paths, run_process=runner)

    def test_should_list_the_recipes_with_their_source_and_wave_as_native(self):
        # Act
        document = recipe_list(argparse.Namespace(), self.runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "recipes": [
                    {"name": "review", "source": "project"},
                    {"name": "nightly", "source": "machine"},
                    {"name": "wave", "source": "native"},
                ],
            },
        )

    def test_should_print_the_name_and_the_source_of_each_recipe(self):
        # Arrange
        document = {
            "schema_version": 1,
            "recipes": [{"name": "review", "source": "project"}, {"name": "wave", "source": "native"}],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "name    source\nreview  project\nwave    native")
