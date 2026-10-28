import argparse
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from brigade.add_command_parsers import add_command_parsers
from brigade.commands.corpus import COMMAND, corpus
from brigade.errors import BrigadeError, ToolNotFound
from tests.unit.commands.command_runtime import ProcessAnswer, ScriptedProcessRunner

PROJECTS = json.dumps({"entities": [{"type": "PROJECT", "name": "app"}]})
APP = json.dumps({"fields": [{"name": "PATH", "atoms": ['"/srv/app"']}]})
WORKTREES = (
    "worktree /srv/app\0HEAD 8885daa\0branch refs/heads/main\0\0"
    "worktree /srv/app-b42\0HEAD de446f3\0branch refs/heads/b42\0\0"
)
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

NO_VIEW = {"type": None, "field": None, "entity": None}
TASKS_OF_THE_WORKTREE = json.dumps(
    {
        "types": [{"type": "TASK"}],
        "entities": [
            {
                "type": "TASK",
                "name": "B30",
                "target": "@TASK.B30",
                "file": "/srv/app-b42/corpus/tasks.awawa",
                "line": 40,
                "status": "todo",
            }
        ],
    }
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
        self.runtime = create_test_runtime(create_test_paths(Path(self.root.name)), run_process=runner.run)
        self.runtime.paths.config_root.mkdir(parents=True)
        self.runtime.paths.schema_file.write_text("SCHEMA PROJECT\n")

    def test_should_read_the_tree_of_the_worktree_in_place(self):
        # Arrange
        request = argparse.Namespace(project="app", ref=None, worktree=Path("/srv/app-b42"), **NO_VIEW)

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
        request = argparse.Namespace(project="app", ref="worktree:main", worktree=None, **NO_VIEW)

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


class CorpusViewOfATypeTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.runner = ScriptedProcessRunner(
            {
                ("awawa", "status", "PROJECT"): ProcessAnswer(stdout=PROJECTS),
                ("awawa", "show", "@PROJECT.app"): ProcessAnswer(stdout=APP),
                ("git", "worktree", "list"): ProcessAnswer(stdout=WORKTREES),
                ("awawa", "status", "TASK"): ProcessAnswer(stdout=TASKS_OF_THE_WORKTREE),
                ("awawa-web", "--help"): ProcessAnswer(),
            }
        )
        self.runtime = create_test_runtime(create_test_paths(Path(self.root.name)), run_process=self.runner.run)
        self.runtime.paths.config_root.mkdir(parents=True)
        self.runtime.paths.schema_file.write_text("SCHEMA PROJECT\n")
        self.request = argparse.Namespace(
            project="app", ref=None, worktree=Path("/srv/app-b42"), type="TASK", field=None, entity=None
        )

    def test_should_link_each_entity_to_its_line_with_the_ide_link_of_the_configuration(self):
        # Arrange
        self.runtime.paths.configuration_file.write_text('ide_link = "idea://open?file={path}&line={line}"\n')

        # Act
        document = corpus(self.request, self.runtime)

        # Assert
        self.assertEqual(
            document["entities"][0]["ide_link"], "idea://open?file=/srv/app-b42/corpus/tasks.awawa&line=40"
        )

    def test_should_link_to_awawa_web_when_it_is_on_the_path(self):
        # Arrange
        rows = [("on the PATH", ProcessAnswer(), "http://127.0.0.1:7878/"), ("absent", ToolNotFound("awawa-web"), None)]
        for case, answer, expected in rows:
            with self.subTest(case=case):
                self.runner.answers["awawa-web", "--help"] = answer

                # Act
                document = corpus(self.request, self.runtime)

                # Assert
                self.assertEqual(document["awawa_web"], expected)

    def test_should_refuse_a_board_or_an_entity_without_a_type(self):
        # Arrange
        rows = [("a board", {"field": "STATUS"}), ("an entity", {"entity": "@TASK.B30"})]
        for case, view in rows:
            with self.subTest(case=case):
                request = argparse.Namespace(project="app", ref=None, worktree=Path("/srv/app-b42"), **NO_VIEW | view)

                # Act
                with self.assertRaises(BrigadeError) as raised:
                    corpus(request, self.runtime)

                # Assert
                self.assertEqual(str(raised.exception), "--field and --entity read the entities of --type")


class CorpusWithAConfigurationThatIsNotTomlTest(unittest.TestCase):
    def test_should_report_the_configuration_before_a_missing_operational_corpus(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        runtime = create_test_runtime(create_test_paths(root))
        runtime.paths.config_root.mkdir(parents=True)
        runtime.paths.configuration_file.write_text('client = "claude-code\n', encoding="utf-8")
        request = argparse.Namespace(project="app", ref="main", worktree=None, **NO_VIEW)

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
        options = argparse.Namespace(project="app", ref="main", worktree=None, **NO_VIEW)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertEqual(request, argparse.Namespace(project="app", ref="main", worktree=None, **NO_VIEW))


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

    def test_should_print_the_entities_the_board_and_the_dependencies_it_read(self):
        # Arrange
        document = {
            "schema_version": 1,
            "project": "app",
            "ref": "main",
            "sha": "de446f3",
            "kind": "archive",
            "root": "/cache/brigade/refs/app/de446f3",
            "type": "TASK",
            "types": ["TASK"],
            "entities": [
                {"target": "@TASK.B27", "status": "implemented", "file": "corpus/tasks.awawa", "line": 12},
                {"target": "@TASK.B30", "status": "todo", "file": "corpus/tasks.awawa", "line": 40},
            ],
            "awawa_web": None,
            "field": "STATUS",
            "board": [{"value": "implemented", "targets": ["@TASK.B27"]}, {"value": None, "targets": ["@TASK.B30"]}],
            "dependencies": {"entity": "@TASK.B30", "reaches": [], "referenced_by": ["@TASK.B32"]},
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "@PROJECT.app\nref   main\nsha   de446f3\nkind  archive\nroot  /cache/brigade/refs/app/de446f3\n"
            "@TASK.B27  implemented  corpus/tasks.awawa:12\n"
            "@TASK.B30  todo  corpus/tasks.awawa:40\n"
            "STATUS implemented: @TASK.B27\n"
            "no STATUS: @TASK.B30\n"
            "@TASK.B30 reaches nothing\n"
            "@TASK.B30 is referenced by @TASK.B32",
        )

    def test_should_print_nothing_for_what_references_an_entity_nothing_references(self):
        # Arrange
        document = {
            "schema_version": 1,
            "project": "app",
            "ref": "main",
            "sha": "de446f3",
            "kind": "archive",
            "root": "/cache/brigade/refs/app/de446f3",
            "dependencies": {"entity": "@TASK.B30", "reaches": [{"target": "@TASK.B27"}], "referenced_by": []},
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "@PROJECT.app\nref   main\nsha   de446f3\nkind  archive\nroot  /cache/brigade/refs/app/de446f3\n"
            "@TASK.B30 reaches @TASK.B27\n"
            "@TASK.B30 is referenced by nothing",
        )
