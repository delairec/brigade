import tempfile
import unittest
from pathlib import Path

from brigade.recipes.read_project_commands import read_project_commands
from brigade.recipes.recipe_places import RecipePlaces
from brigade.system.validate_document import DocumentInvalid
from tests.unit.recipes.recipe_files import write_recipe
from tests.unit.refuse_to_run import refuse_to_run

NO_CORPUS = None
ACCEPTANCE_RECIPE = """schema_version = 1
name = "acceptance"
description = "the light checks of the shop"
params = []
max_wall = 30

[[steps]]
kind = "command"
argv = ["python3", "-m", "unittest"]

[[steps]]
kind = "command"
argv = ["ruff", "check", "."]
"""
ACCEPTANCE_RECIPE_WITH_A_GATE_STEP = """schema_version = 1
name = "acceptance"
description = "the light checks of the shop"
params = []
max_wall = 30

[[steps]]
kind = "command"
argv = ["python3", "-m", "unittest"]

[[steps]]
kind = "gate"
preflight = "ancestry"
"""
ACCEPTANCE_RECIPE_WITH_AN_ARGV_STRING = """schema_version = 1
name = "acceptance"
description = "the light checks of the shop"
params = []
max_wall = 30

[[steps]]
kind = "command"
argv = "python3 -m unittest"
"""


class ReadProjectCommandsTest(unittest.TestCase):
    def setUp(self):
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        self.root = Path(root.name)
        self.project_recipes = self.root / "shop" / ".brigade" / "recipes"
        self.machine = self.root / "config" / "recipes"
        self.built_ins = self.root / "brigade" / "recipes" / "data"
        self.places = RecipePlaces(NO_CORPUS, self.project_recipes, self.machine, self.built_ins)

    def test_should_read_the_argv_of_each_command_step_of_the_recipe_of_the_project(self):
        # Arrange
        self.project_recipes.mkdir(parents=True)
        (self.project_recipes / "acceptance.toml").write_text(ACCEPTANCE_RECIPE)

        # Act
        commands = read_project_commands(self.places, "acceptance", refuse_to_run)

        # Assert
        self.assertEqual(commands, (("python3", "-m", "unittest"), ("ruff", "check", ".")))

    def test_should_read_no_command_when_the_project_has_no_recipe_of_that_name(self):
        # Arrange
        write_recipe(self.machine, "acceptance", "the machine's acceptance")
        write_recipe(self.built_ins, "acceptance", "the built-in acceptance")

        # Act
        commands = read_project_commands(self.places, "acceptance", refuse_to_run)

        # Assert
        self.assertEqual(commands, ())

    def test_should_refuse_a_recipe_of_the_project_holding_a_step_that_is_no_command_step(self):
        # Arrange
        self.project_recipes.mkdir(parents=True)
        (self.project_recipes / "acceptance.toml").write_text(ACCEPTANCE_RECIPE_WITH_A_GATE_STEP)

        # Act
        with self.assertRaises(DocumentInvalid) as refusal:
            read_project_commands(self.places, "acceptance", refuse_to_run)

        # Assert
        self.assertEqual(
            str(refusal.exception), "the recipe acceptance of the project: steps[1].kind is 'gate', not one of command"
        )

    def test_should_refuse_a_recipe_of_the_project_whose_argv_is_a_string(self):
        # Arrange
        self.project_recipes.mkdir(parents=True)
        (self.project_recipes / "acceptance.toml").write_text(ACCEPTANCE_RECIPE_WITH_AN_ARGV_STRING)

        # Act
        with self.assertRaises(DocumentInvalid) as refusal:
            read_project_commands(self.places, "acceptance", refuse_to_run)

        # Assert
        self.assertEqual(
            str(refusal.exception), "the recipe acceptance of the project: steps[0].argv is a string, not a list"
        )
