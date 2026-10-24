import argparse
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from brigade.add_command_parsers import add_command_parsers
from brigade.commands.corpus import COMMAND, corpus
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import ProcessAnswer, ScriptedProcessRunner

PROJECTS = json.dumps({"entities": [{"type": "PROJECT", "name": "app"}]})
APP = json.dumps({"fields": [{"name": "PATH", "atoms": ['"/srv/app"']}]})
WORKTREES = (
    "worktree /srv/app\0HEAD 8885daa\0branch refs/heads/main\0\0"
    "worktree /srv/app-b42\0HEAD de446f3\0branch refs/heads/b42\0\0"
)
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime


class CorpusOfAWorktreeTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        runner = ScriptedProcessRunner(
            {
                ("awawa", "status", "PROJECT"): ProcessAnswer(stdout=PROJECTS),
                ("awawa", "show", "@PROJECT.app"): ProcessAnswer(stdout=APP),
                ("git", "worktree", "list"): ProcessAnswer(stdout=WORKTREES),
            }
        )
        self.runtime = create_test_runtime(create_test_paths(Path(self.root.name)), run_process=runner.run)
        self.runtime.paths.config_root.mkdir(parents=True)
        self.runtime.paths.schema_file.write_text("SCHEMA PROJECT\n")

    def test_should_read_the_tree_of_the_worktree_in_place(self):
        # Arrange
        request = argparse.Namespace(project="app", ref=None, worktree=Path("/srv/app-b42"))

        # Act
        document = corpus(request, self.runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "project": "app",
                "ref": None,
                "sha": "de446f3",
                "kind": "worktree",
                "root": "/srv/app-b42",
            },
        )

    def test_should_read_the_worktree_holding_the_branch_a_worktree_ref_names(self):
        # Arrange
        request = argparse.Namespace(project="app", ref="worktree:main", worktree=None)

        # Act
        document = corpus(request, self.runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "project": "app",
                "ref": "worktree:main",
                "sha": "8885daa",
                "kind": "worktree",
                "root": "/srv/app",
            },
        )


class CorpusWithAConfigurationThatIsNotTomlTest(unittest.TestCase):
    def test_should_report_the_configuration_before_a_missing_operational_corpus(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        runtime = create_test_runtime(create_test_paths(root))
        runtime.paths.config_root.mkdir(parents=True)
        runtime.paths.configuration_file.write_text('client = "claude-code\n', encoding="utf-8")
        request = argparse.Namespace(project="app", ref="main", worktree=None)

        # Act
        with self.assertRaises(BrigadeError) as raised:
            corpus(request, runtime)

        # Assert
        self.assertIn(f"{runtime.paths.configuration_file} is not valid TOML: ", str(raised.exception))


class CorpusArgumentsTest(unittest.TestCase):
    def parse(self, *arguments: str) -> int:
        parser = argparse.ArgumentParser(prog="brigade")
        add_command_parsers(parser, [COMMAND], argparse.ArgumentParser(add_help=False))
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exit_:
            parser.parse_args(["corpus", "app", *arguments])
        return exit_.exception.code

    def test_should_refuse_a_ref_and_a_worktree_together(self):
        # Act
        exit_code = self.parse("--ref", "main", "--worktree", "/srv/app")

        # Assert
        self.assertEqual(exit_code, 2)

    def test_should_require_a_ref_or_a_worktree(self):
        # Act
        exit_code = self.parse()

        # Assert
        self.assertEqual(exit_code, 2)


class CorpusRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_they_are(self):
        # Arrange
        options = argparse.Namespace(project="app", ref="main", worktree=None)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertEqual(request, argparse.Namespace(project="app", ref="main", worktree=None))


class CorpusExitCodeTest(unittest.TestCase):
    def test_should_exit_0_once_the_tree_is_ready(self):
        # Arrange
        document = {"project": "app", "sha": "de446f3"}

        # Act
        exit_code = COMMAND.decide_exit_code(document)

        # Assert
        self.assertEqual(exit_code, 0)


class CorpusTextTest(unittest.TestCase):
    def test_should_print_the_fields_of_the_tree_it_knows(self):
        # Arrange
        document = {
            "schema_version": 1,
            "project": "app",
            "ref": None,
            "sha": "de446f3",
            "kind": "worktree",
            "root": "/srv/app-b42",
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "@PROJECT.app\nsha   de446f3\nkind  worktree\nroot  /srv/app-b42")

    def test_should_print_the_ref_of_a_tree_extracted_at_a_branch(self):
        # Arrange
        document = {
            "schema_version": 1,
            "project": "app",
            "ref": "main",
            "sha": "de446f3",
            "kind": "archive",
            "root": "/cache/brigade/refs/app/de446f3",
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text, "@PROJECT.app\nref   main\nsha   de446f3\nkind  archive\nroot  /cache/brigade/refs/app/de446f3"
        )
