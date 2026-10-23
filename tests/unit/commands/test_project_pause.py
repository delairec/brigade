import argparse
import json
import tempfile
import unittest
from pathlib import Path

from brigade.commands.project_pause import COMMAND, project_pause
from tests.unit.commands.command_runtime import ProcessAnswer, ScriptedProcessRunner

PROJECTS = json.dumps({"entities": [{"type": "PROJECT", "name": "app"}]})
PAUSED_APP = json.dumps(
    {"fields": [{"name": "PATH", "atoms": ['"/srv/app"']}, {"name": "STATUS", "atoms": ["paused"]}]}
)
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime


class ProjectPauseTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        runner = ScriptedProcessRunner(
            {
                ("awawa", "status", "PROJECT"): ProcessAnswer(stdout=PROJECTS),
                ("awawa", "show", "@PROJECT.app"): ProcessAnswer(stdout=PAUSED_APP),
            }
        )
        self.runtime = create_test_runtime(create_test_paths(Path(self.root.name)), run_process=runner.run)
        self.runtime.paths.config_root.mkdir(parents=True)
        self.runtime.paths.schema_file.write_text("SCHEMA PROJECT\n")

    def test_should_leave_a_project_already_paused_unchanged(self):
        # Arrange
        request = argparse.Namespace(name="app")

        # Act
        document = project_pause(request, self.runtime)

        # Assert
        self.assertEqual(document, {"schema_version": 1, "project": "app", "status": "paused", "changed": False})


class ProjectPauseRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_they_are(self):
        # Arrange
        options = argparse.Namespace(name="app")

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertEqual(request, argparse.Namespace(name="app"))


class ProjectPauseExitCodeTest(unittest.TestCase):
    def test_should_exit_0_once_the_status_is_settled(self):
        # Arrange
        document = {"project": "app", "status": "paused", "changed": False}

        # Act
        exit_code = COMMAND.decide_exit_code(document)

        # Assert
        self.assertEqual(exit_code, 0)


class ProjectPauseTextTest(unittest.TestCase):
    def test_should_name_the_project_it_paused(self):
        # Arrange
        document = {"schema_version": 1, "project": "app", "status": "paused", "changed": True}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "paused @PROJECT.app")

    def test_should_name_the_status_the_project_already_had(self):
        # Arrange
        document = {"schema_version": 1, "project": "app", "status": "paused", "changed": False}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "@PROJECT.app is already paused")
