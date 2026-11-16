import argparse
import contextlib
import json
import tempfile
import unittest
from pathlib import Path

from brigade.commands.recipe_list import COMMAND, recipe_list
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.recipes.checkout_answers import create_checkout_answers
from tests.unit.recipes.recipe_entity import REVIEW_RECIPE_ENTITY
from tests.unit.recipes.recipe_files import write_recipe
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner
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
        self.root_path = root
        self.paths = paths
        self.enterContext(contextlib.chdir(root / "shop"))
        runner = RecordingProcessRunner(
            {
                **create_registry_answers(paths.config_root, NO_PROJECT_REGISTERED),
                **create_checkout_answers(root / "shop", root / "shop"),
            }
        )
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

    def test_should_list_the_recipe_entities_of_the_registered_project_from_a_directory_of_its_worktree(self):
        # Arrange
        project = self.root_path / "shop"
        worktree = project / ".brigade" / "worktrees" / "B1"
        (worktree / "src").mkdir(parents=True)
        self.enterContext(contextlib.chdir(worktree / "src"))
        corpus = str(project / "corpus")
        runner = RecordingProcessRunner(
            {
                **create_registry_answers(
                    self.paths.config_root, {"shop": {"PATH": str(project), "CORPUS": "corpus", "MODE": "area"}}
                ),
                **create_checkout_answers(worktree, project),
                ("awawa", "status", "--json", corpus): ProcessAnswer(
                    stdout=json.dumps({"entities": [{"type": "RECIPE", "name": "triage"}]})
                ),
                ("awawa", "show", "@RECIPE.triage", "--json", corpus): ProcessAnswer(
                    stdout=json.dumps({**REVIEW_RECIPE_ENTITY, "name": "triage"})
                ),
            }
        )
        runtime = create_test_runtime(self.paths, run_process=runner)

        # Act
        document = recipe_list(argparse.Namespace(), runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "recipes": [
                    {"name": "triage", "source": "project"},
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
