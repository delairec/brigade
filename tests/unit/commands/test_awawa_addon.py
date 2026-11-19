import argparse
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from brigade.commands.awawa_addon import COMMAND, awawa_addon
from brigade.errors import ToolNotFound
from tests.unit.commands.command_runtime import ProcessAnswer, ScriptedProcessRunner
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

PROJECTS = json.dumps({"entities": [{"type": "PROJECT", "name": "app"}]})
APP = json.dumps({"fields": [{"name": "PATH", "atoms": ['"/srv/app"']}]})


class AwawaAddonTest(unittest.TestCase):
    def setUp(self):
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        self.paths = create_test_paths(Path(root.name))
        self.paths.config_root.mkdir(parents=True)
        self.paths.schema_file.write_text("SCHEMA PROJECT\n")

    def test_should_announce_its_start_then_answer_each_request_line(self):
        # Arrange
        runner = ScriptedProcessRunner(
            {
                ("awawa", "--version"): ProcessAnswer(stdout="awawa 2.7.0\n"),
                ("awawa", "status", "PROJECT"): ProcessAnswer(stdout=PROJECTS),
                ("awawa", "show", "@PROJECT.app"): ProcessAnswer(stdout=APP),
            }
        )
        request = argparse.Namespace(standard_input=io.StringIO('{"project": "shop", "view": "tree"}\n'))

        # Act
        with contextlib.redirect_stdout(io.StringIO()) as written:
            document = awawa_addon(request, create_test_runtime(self.paths, run_process=runner.run))

        # Assert
        self.assertEqual(written.getvalue(), '{"awawa": "2.7.0"}\n{"error": "@PROJECT.shop is not registered"}\n')
        self.assertEqual(document, {"schema_version": 1, "answered": 1})

    def test_should_fail_to_start_without_writing_anything_when_awawa_is_absent(self):
        # Arrange
        runner = ScriptedProcessRunner({("awawa",): ToolNotFound("awawa not on PATH")})
        request = argparse.Namespace(standard_input=io.StringIO(""))

        # Act
        with contextlib.redirect_stdout(io.StringIO()) as written, self.assertRaises(ToolNotFound) as raised:
            awawa_addon(request, create_test_runtime(self.paths, run_process=runner.run))

        # Assert
        self.assertEqual(str(raised.exception), "awawa not on PATH")
        self.assertEqual(written.getvalue(), "")


class AwawaAddonTextTest(unittest.TestCase):
    def test_should_say_how_many_requests_it_answered(self):
        # Arrange
        document = {"schema_version": 1, "answered": 3}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "answered 3 requests of the awawa tab")
