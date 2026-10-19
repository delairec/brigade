import argparse
import json
import tempfile
import unittest
from pathlib import Path

from brigade.commands.project_show import COMMAND, project_show
from tests.unit.commands.command_runtime import ProcessAnswer, ScriptedProcessRunner, create_runtime

PROJECTS = json.dumps({"entities": [{"type": "PROJECT", "name": "app"}]})
APP = json.dumps({"fields": [{"name": "PATH", "atoms": ['"/srv/app"']}, {"name": "STATUS", "atoms": ["active"]}]})


class ProjectShowTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        runner = ScriptedProcessRunner(
            {
                ("awawa", "status", "PROJECT"): ProcessAnswer(stdout=PROJECTS),
                ("awawa", "show", "@PROJECT.app"): ProcessAnswer(stdout=APP),
            }
        )
        self.runtime = create_runtime(Path(self.root.name), run_process=runner.run)
        self.runtime.paths.config_root.mkdir(parents=True)
        self.runtime.paths.schema_file.write_text("SCHEMA PROJECT\n")

    def test_should_give_the_fields_of_the_project(self):
        # Arrange
        request = argparse.Namespace(name="app")

        # Act
        document = project_show(request, self.runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "project": {
                    "name": "app",
                    "fields": [{"name": "PATH", "value": "/srv/app"}, {"name": "STATUS", "value": "active"}],
                },
            },
        )


class ProjectShowRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_they_are(self):
        # Arrange
        options = argparse.Namespace(name="app")

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertEqual(request, argparse.Namespace(name="app"))


class ProjectShowExitCodeTest(unittest.TestCase):
    def test_should_exit_0_once_the_project_is_shown(self):
        # Arrange
        document = {"project": {"name": "app", "fields": []}}

        # Act
        exit_code = COMMAND.decide_exit_code(document)

        # Assert
        self.assertEqual(exit_code, 0)


class ProjectShowTextTest(unittest.TestCase):
    def test_should_print_one_field_per_line_under_the_project(self):
        # Arrange
        document = {
            "project": {
                "name": "app",
                "fields": [{"name": "PATH", "value": "/srv/app"}, {"name": "STATUS", "value": "active"}],
            }
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "@PROJECT.app\nPATH        /srv/app\nSTATUS      active")
