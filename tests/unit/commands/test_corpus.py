import argparse
import json
import tempfile
import unittest
from pathlib import Path

from brigade.commands.corpus import COMMAND, corpus
from tests.unit.commands.create_command_runtime import create_command_runtime
from tests.unit.commands.scripted_process_runner import ProcessAnswer, ScriptedProcessRunner

PROJECTS = json.dumps({"entities": [{"type": "PROJECT", "name": "app"}]})
APP = json.dumps({"fields": [{"name": "PATH", "atoms": ['"/srv/app"']}]})
WORKTREES = (
    "worktree /srv/app\0HEAD 8885daa\0branch refs/heads/main\0\0"
    "worktree /srv/app-b42\0HEAD de446f3\0branch refs/heads/b42\0\0"
)


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
        self.runtime = create_command_runtime(Path(self.root.name), run_process=runner.run)
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
