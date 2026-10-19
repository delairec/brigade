import argparse
import json
import tempfile
import unittest
from pathlib import Path

from brigade.commands.project_list import COMMAND, project_list
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import ProcessAnswer, ScriptedProcessRunner, create_runtime

PROJECTS = json.dumps(
    {
        "entities": [
            {"type": "PROJECT", "name": "app"},
            {"type": "PROJECT", "name": "lib"},
            {"type": "PROJECT", "name": "?"},
        ]
    }
)
APP = json.dumps({"fields": [{"name": "PATH", "atoms": ['"/srv/app"']}, {"name": "STATUS", "atoms": ["active"]}]})
LIB = json.dumps({"fields": [{"name": "PATH", "atoms": ['"/srv/lib"']}]})


class ProjectListTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        runner = ScriptedProcessRunner(
            {
                ("awawa", "status", "PROJECT"): ProcessAnswer(stdout=PROJECTS),
                ("awawa", "show", "@PROJECT.app"): ProcessAnswer(stdout=APP),
                ("awawa", "show", "@PROJECT.lib"): ProcessAnswer(stdout=LIB),
            }
        )
        self.runtime = create_runtime(Path(self.root.name), run_process=runner.run)

    def test_should_list_each_project_with_its_status_and_path(self):
        # Arrange
        self.runtime.paths.config_root.mkdir(parents=True)
        self.runtime.paths.schema_file.write_text("SCHEMA PROJECT\n")
        no_option = argparse.Namespace()

        # Act
        document = project_list(no_option, self.runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "projects": [
                    {"name": "app", "path": "/srv/app", "status": "active"},
                    {"name": "lib", "path": "/srv/lib", "status": ""},
                ],
            },
        )

    def test_should_refuse_without_the_operational_corpus(self):
        # Arrange
        no_option = argparse.Namespace()

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            project_list(no_option, self.runtime)

        # Assert
        self.assertEqual(str(refusal.exception), "the operational corpus is missing; run brigade init first")


class ProjectListRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_they_are(self):
        # Arrange
        options = argparse.Namespace(json=True)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertEqual(request, argparse.Namespace(json=True))


class ProjectListExitCodeTest(unittest.TestCase):
    def test_should_exit_0_once_the_projects_are_listed(self):
        # Arrange
        document = {"projects": []}

        # Act
        exit_code = COMMAND.decide_exit_code(document)

        # Assert
        self.assertEqual(exit_code, 0)


class ProjectListTextTest(unittest.TestCase):
    def test_should_print_one_row_per_project(self):
        # Arrange
        document = {
            "projects": [
                {"name": "app", "path": "/srv/app", "status": "active"},
                {"name": "library", "path": "/srv/lib", "status": ""},
            ]
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "name     status  path\napp      active  /srv/app\nlibrary          /srv/lib")

    def test_should_say_that_no_project_is_registered(self):
        # Arrange
        document = {"projects": []}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "no project registered")
