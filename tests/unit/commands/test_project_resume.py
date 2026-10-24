import argparse
import json
import tempfile
import unittest
from pathlib import Path

from brigade.commands.project_resume import COMMAND, project_resume
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import ProcessAnswer, ScriptedProcessRunner

PROJECTS = json.dumps({"entities": [{"type": "PROJECT", "name": "app"}]})
PAUSED_APP = json.dumps(
    {"fields": [{"name": "PATH", "atoms": ['"/srv/app"']}, {"name": "STATUS", "atoms": ["paused"]}]}
)
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

REGISTRY = 'PROJECT app\n\tPATH "/srv/app"\n\tSTATUS paused\n'


class ProjectResumeTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        runner = ScriptedProcessRunner(
            {
                ("awawa", "status", "PROJECT"): ProcessAnswer(stdout=PROJECTS),
                ("awawa", "show", "@PROJECT.app"): ProcessAnswer(stdout=PAUSED_APP),
                ("awawa", "fmt"): ProcessAnswer(),
                ("awawa", "lint"): ProcessAnswer(),
                ("git", "add"): ProcessAnswer(),
                ("git", "diff"): ProcessAnswer(exit_code=1),
                ("git", "commit"): ProcessAnswer(),
            }
        )
        self.runtime = create_test_runtime(create_test_paths(Path(self.root.name)), run_process=runner.run)
        self.runtime.paths.config_root.mkdir(parents=True)
        self.runtime.paths.schema_file.write_text("SCHEMA PROJECT\n")
        (self.runtime.paths.config_root / "projects.awawa").write_text(REGISTRY)

    def test_should_set_the_paused_project_active(self):
        # Arrange
        request = argparse.Namespace(name="app")

        # Act
        document = project_resume(request, self.runtime)

        # Assert
        self.assertEqual(document, {"schema_version": 1, "project": "app", "status": "active", "changed": True})


class ProjectResumeRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_they_are(self):
        # Arrange
        options = argparse.Namespace(name="app")

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertEqual(request, argparse.Namespace(name="app"))


class ProjectResumeExitCodeTest(unittest.TestCase):
    def test_should_exit_0_once_the_status_is_settled(self):
        # Arrange
        document = {"project": "app", "status": "active", "changed": False}

        # Act
        exit_code = COMMAND.decide_exit_code(document)

        # Assert
        self.assertEqual(exit_code, 0)


class ProjectResumeTextTest(unittest.TestCase):
    def test_should_name_the_project_it_resumed_or_the_status_it_already_had(self):
        # Arrange
        rows = [(True, "resumed @PROJECT.app"), (False, "@PROJECT.app is already active")]
        for changed, expected in rows:
            with self.subTest(changed=changed):
                document = {"schema_version": 1, "project": "app", "status": "active", "changed": changed}

                # Act
                text = COMMAND.render_text(document)

                # Assert
                self.assertEqual(text, expected)


class ProjectResumeBeforeInitTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.runtime = create_test_runtime(create_test_paths(Path(self.root.name)))

    def test_should_refuse_without_the_operational_corpus(self):
        # Arrange
        request = argparse.Namespace(name="app")

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            project_resume(request, self.runtime)

        # Assert
        self.assertEqual(str(refusal.exception), "the operational corpus is missing; run brigade init first")
