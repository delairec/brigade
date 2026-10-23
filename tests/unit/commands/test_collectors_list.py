import argparse
import contextlib
import json
import tempfile
import unittest
from pathlib import Path

from brigade.commands.collectors_list import COMMAND, collectors_list
from tests.unit.commands.command_runtime import ProcessAnswer, ScriptedProcessRunner
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

PROJECTS = json.dumps({"entities": [{"type": "PROJECT", "name": "app"}]})


def _place_executable(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\n")
    path.chmod(0o755)


class CollectorsListTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        root = Path(self.root.name).resolve()
        project = root / "app"
        _place_executable(project / ".brigade" / "collectors" / "notes")
        _place_executable(root / "bin" / "brigade-collector-weather")
        self.enterContext(contextlib.chdir(project))
        app = json.dumps(
            {"fields": [{"name": "PATH", "atoms": [json.dumps(str(project))]}, {"name": "FORGE", "atoms": ['"none"']}]}
        )
        runner = ScriptedProcessRunner(
            {
                ("awawa", "status", "PROJECT"): ProcessAnswer(stdout=PROJECTS),
                ("awawa", "show", "@PROJECT.app"): ProcessAnswer(stdout=app),
            }
        )
        self.runtime = create_test_runtime(
            create_test_paths(root, executable_search_path=str(root / "bin")), run_process=runner.run
        )
        _place_executable(self.runtime.paths.config_root / "collectors" / "backlog")
        self.no_option = argparse.Namespace()

    def test_should_list_the_collectors_of_the_project_the_machine_and_the_path_first(self):
        # Act
        document = collectors_list(self.no_option, self.runtime)

        # Assert
        self.assertEqual(
            document["collectors"][:3],
            [
                {"name": "notes", "source": "project", "absent": None},
                {"name": "backlog", "source": "machine", "absent": None},
                {"name": "weather", "source": "PATH", "absent": None},
            ],
        )

    def test_should_mark_a_forge_collector_absent_for_a_project_without_a_forge(self):
        # Arrange
        self.runtime.paths.schema_file.write_text("SCHEMA PROJECT\n")

        # Act
        document = collectors_list(self.no_option, self.runtime)

        # Assert
        self.assertIn({"name": "pr-list", "source": "built-in", "absent": "FORGE none"}, document["collectors"])

    def test_should_mark_no_collector_absent_without_the_operational_corpus(self):
        # Act
        document = collectors_list(self.no_option, self.runtime)

        # Assert
        self.assertIn({"name": "pr-list", "source": "built-in", "absent": None}, document["collectors"])


class CollectorsListRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_they_are(self):
        # Arrange
        options = argparse.Namespace(json=True)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertEqual(request, argparse.Namespace(json=True))


class CollectorsListExitCodeTest(unittest.TestCase):
    def test_should_exit_0_once_the_collectors_are_listed(self):
        # Arrange
        document = {"collectors": []}

        # Act
        exit_code = COMMAND.decide_exit_code(document)

        # Assert
        self.assertEqual(exit_code, 0)


class CollectorsListTextTest(unittest.TestCase):
    def test_should_print_one_row_per_collector_with_a_dash_when_present(self):
        # Arrange
        document = {
            "collectors": [
                {"name": "notes", "source": "project", "absent": None},
                {"name": "pr-list", "source": "built-in", "absent": "FORGE none"},
            ]
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "name     source    absent\nnotes    project   -\npr-list  built-in  FORGE none")
