import argparse
import contextlib
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from brigade.commands.recipe_lint import COMMAND, recipe_lint
from brigade.preflights.run_preflight import BUILT_IN_PREFLIGHTS
from brigade.system.resolve_plugin import resolve_plugin
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.recipes.checkout_answers import create_checkout_answers
from tests.unit.recipes.recipe_entity import REVIEW_RECIPE_TOML
from tests.unit.recording_process_runner import RecordingProcessRunner
from tests.unit.registry_answers import create_registry_answers

NO_PROJECT_REGISTERED = {}
NO_PLUGIN_SOURCES = None


@dataclass(frozen=True)
class ClientAdapterDouble:
    EXECUTABLE: str


CLAUDE_CODE = ClientAdapterDouble(EXECUTABLE="claude")


def resolve_plugin_double(kind: str, name: str, **places) -> object:
    if (kind, name) == ("client", "claude-code"):
        return CLAUDE_CODE
    return resolve_plugin(kind, name, sources=NO_PLUGIN_SOURCES, **places)


def place_executable(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\n")
    path.chmod(0o755)


class RecipeLintTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        root = Path(self.root.name).resolve()
        self.paths = create_test_paths(root)
        self.recipes = root / "shop" / ".brigade" / "recipes"
        self.recipes.mkdir(parents=True)
        self.enterContext(contextlib.chdir(root / "shop"))
        runner = RecordingProcessRunner(
            {
                **create_registry_answers(self.paths.config_root, NO_PROJECT_REGISTERED),
                **create_checkout_answers(root / "shop", root / "shop"),
            }
        )
        self.runtime = create_test_runtime(self.paths, run_process=runner, resolve_plugin=resolve_plugin_double)

    def test_should_pass_a_recipe_whose_every_name_resolves(self):
        # Arrange
        (self.recipes / "review.toml").write_text(REVIEW_RECIPE_TOML)

        # Act
        document = recipe_lint(argparse.Namespace(name="review"), self.runtime)

        # Assert
        self.assertEqual(
            document, {"schema_version": 1, "recipe": "review", "source": "project", "result": "ok", "findings": []}
        )

    def test_should_resolve_the_collector_of_the_project_and_refuse_every_other_name_found_nowhere(self):
        # Arrange
        place_executable(self.recipes.parent / "collectors" / "issues")
        (self.recipes / "nightly.toml").write_text(
            'schema_version = 1\nname = "nightly"\ndescription = "nightly"\nparams = []\nmax_wall = 5\n'
            '[[steps]]\nkind = "collect"\ncollector = "issues"\n'
            '[[steps]]\nkind = "gate"\npreflight = "release-readiness"\n'
            '[[steps]]\nkind = "output"\noutput = "slack"\n'
            '[[steps]]\nkind = "judge"\nslot = "review"\nprocedure = "usage-report"\nanswer = "REPORT"\n'
        )

        # Act
        document = recipe_lint(argparse.Namespace(name="nightly"), self.runtime)

        # Assert
        self.assertEqual(
            document["findings"],
            [
                f"steps[1]: no preflight release-readiness: no release-readiness.toml in {BUILT_IN_PREFLIGHTS}",
                "steps[2]: no output slack: no brigade-output-slack on PATH",
                (
                    "steps[3]: no procedure usage-report: not shipped with brigade and no instructions corpus set"
                    " in config.toml"
                ),
            ],
        )

    def test_should_refuse_a_command_step_running_the_binary_of_the_configured_client(self):
        # Arrange
        self.paths.config_root.mkdir(parents=True)
        self.paths.configuration_file.write_text('client = "claude-code"\n')
        (self.recipes / "ask.toml").write_text(
            'schema_version = 1\nname = "ask"\ndescription = "ask"\nparams = []\nmax_wall = 5\n'
            '[[steps]]\nkind = "command"\nargv = ["claude", "-p", "hello"]\n'
        )

        # Act
        document = recipe_lint(argparse.Namespace(name="ask"), self.runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "recipe": "ask",
                "source": "project",
                "result": "fail",
                "findings": ["steps[0]: runs claude, the binary of the configured client"],
            },
        )

    def test_should_fail_a_recipe_holding_a_finding(self):
        # Arrange
        document = {"schema_version": 1, "recipe": "ask", "source": "project", "result": "fail", "findings": ["x"]}

        # Act
        exit_code = COMMAND.decide_exit_code(document)

        # Assert
        self.assertEqual(exit_code, 1)

    def test_should_print_the_verdict_then_each_finding(self):
        # Arrange
        document = {
            "schema_version": 1,
            "recipe": "ask",
            "source": "project",
            "result": "fail",
            "findings": ["steps[0]: no output slack"],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "fail  recipe ask (project)\n  steps[0]: no output slack")
