import argparse
import json
import tempfile
import unittest
from pathlib import Path

from brigade.commands.corpus_awawa import COMMAND, AwawaPassage, corpus_awawa
from brigade.system.run_process import ProcessRecord
from tests.unit.commands.create_command_runtime import create_command_runtime
from tests.unit.commands.scripted_process_runner import ProcessAnswer, ScriptedProcessRunner

PROJECTS = json.dumps({"entities": [{"type": "PROJECT", "name": "app"}]})
APP = json.dumps({"fields": [{"name": "PATH", "atoms": ['"/srv/app"']}]})
WORKTREES = "worktree /srv/app-b42\0HEAD de446f3\0branch refs/heads/b42\0\0"
LINT_RECORD = ProcessRecord(
    argv=("awawa", "lint", "--strict", "."),
    cwd="/srv/app-b42",
    exit_code=1,
    stdout="corpus/tasks.awawa:3: L025\n",
    stderr="1 finding\n",
    duration_ms=0,
)


class CorpusAwawaTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        runner = ScriptedProcessRunner(
            {
                ("awawa", "status", "PROJECT"): ProcessAnswer(stdout=PROJECTS),
                ("awawa", "show", "@PROJECT.app"): ProcessAnswer(stdout=APP),
                ("git", "worktree", "list"): ProcessAnswer(stdout=WORKTREES),
                ("awawa", "lint"): ProcessAnswer(
                    stdout="corpus/tasks.awawa:3: L025\n", exit_code=1, stderr="1 finding\n"
                ),
            }
        )
        self.runtime = create_command_runtime(Path(self.root.name), run_process=runner.run)
        self.runtime.paths.config_root.mkdir(parents=True)
        self.runtime.paths.schema_file.write_text("SCHEMA PROJECT\n")

    def test_should_pass_the_run_of_awawa_in_the_tree_through(self):
        # Arrange
        request = argparse.Namespace(
            project="app", ref="worktree:b42", worktree=None, passed_arguments=("lint", "--strict", ".")
        )

        # Act
        passage = corpus_awawa(request, self.runtime)

        # Assert
        self.assertEqual(passage, AwawaPassage(project="app", sha="de446f3", record=LINT_RECORD))


class CorpusAwawaRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_they_are(self):
        # Arrange
        options = argparse.Namespace(project="app", passed_arguments=("status",))

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertEqual(request, argparse.Namespace(project="app", passed_arguments=("status",)))


class CorpusAwawaPassageTest(unittest.TestCase):
    def setUp(self):
        self.passage = AwawaPassage(project="app", sha="de446f3", record=LINT_RECORD)

    def test_should_print_the_stdout_of_awawa(self):
        # Act
        text = COMMAND.render_text(self.passage)

        # Assert
        self.assertEqual(text, "corpus/tasks.awawa:3: L025\n")

    def test_should_pass_the_stderr_of_awawa(self):
        # Act
        stderr = COMMAND.render_passed_stderr(self.passage)

        # Assert
        self.assertEqual(stderr, "1 finding\n")

    def test_should_exit_with_the_exit_code_of_awawa(self):
        # Act
        exit_code = COMMAND.decide_exit_code(self.passage)

        # Assert
        self.assertEqual(exit_code, 1)

    def test_should_name_the_project_and_the_commit_awawa_read(self):
        # Act
        diagnostics = COMMAND.describe_diagnostics(self.passage)

        # Assert
        self.assertEqual(diagnostics, ["@PROJECT.app at de446f3"])
