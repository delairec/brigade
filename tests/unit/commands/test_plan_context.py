import argparse
import json
import tempfile
import unittest
from pathlib import Path

from brigade.commands.plan_context import COMMAND, plan_context
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import ProcessAnswer, ScriptedProcessRunner

REQUEST = json.dumps(
    {
        "fields": [
            {"name": "PROJECT", "atoms": ["@PROJECT.app"]},
            {"name": "TEXT", "atoms": ['"Let the tides be planned"']},
            {"name": "STATUS", "atoms": ["planning"]},
        ]
    }
)
PROJECTS = json.dumps({"entities": [{"type": "PROJECT", "name": "app"}]})
MAIN_SHA = "4f1c2a9"
FORGE_MAIN_SHA = "9b0d3e7"
APP = json.dumps(
    {
        "fields": [
            {"name": "PATH", "atoms": ['"/srv/app"']},
            {"name": "MAIN", "atoms": ['"main"']},
            {"name": "CORPUS", "atoms": ['"corpus"']},
            {"name": "FORGE", "atoms": ['"none"']},
        ]
    }
)
APP_ON_GITHUB = json.dumps(
    {
        "fields": [
            {"name": "PATH", "atoms": ['"/srv/app"']},
            {"name": "MAIN", "atoms": ['"main"']},
            {"name": "CORPUS", "atoms": ['"corpus"']},
            {"name": "FORGE", "atoms": ['"github"']},
        ]
    }
)
APP_WITHOUT_CORPUS = json.dumps({"fields": [{"name": "PATH", "atoms": ['"/srv/app"']}]})
CORPUS_STATUS = json.dumps(
    {
        "types": [{"type": "TASK", "total": 2, "counts": {"draft": 1, "todo": 1, "done": 0}}],
        "entities": [
            {"type": "SCHEMA", "name": "TASK", "target": "@SCHEMA.TASK"},
            {"type": "TASK", "name": "T7", "target": "@TASK.T7"},
            {"type": "DECISION", "name": "D1", "target": "@DECISION.D1"},
        ],
    }
)
TASK_T7 = json.dumps(
    {
        "type": "TASK",
        "name": "T7",
        "status": "draft",
        "fields": [
            {"name": "TITLE", "atoms": ['"Ebb the tide"'], "fields": []},
            {
                "name": "SPEC",
                "atoms": ['"the tide ebbs"'],
                "fields": [{"name": "IMPL", "atoms": ['"brigade/tides.py::ebb"'], "fields": []}],
            },
        ],
    }
)
DECISION_D1 = json.dumps(
    {
        "type": "DECISION",
        "name": "D1",
        "status": "active",
        "fields": [{"name": "TITLE", "atoms": ['"Tides run on the clock"'], "fields": []}],
    }
)
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

TASK_SCHEMA = json.dumps({"fields": [{"name": "FIELD", "atoms": ["TITLE"]}]})
FORGE = object()


def resolve_forge(kind: str, name: str, **places):
    return FORGE


class PlanContextTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.main_tree = Path(self.root.name) / "cache" / "refs" / "app" / MAIN_SHA
        self.main_tree.mkdir(parents=True)
        self.answers = {
            ("awawa", "show", "@REQUEST.r1"): ProcessAnswer(stdout=REQUEST),
            ("awawa", "status", "PROJECT"): ProcessAnswer(stdout=PROJECTS),
            ("awawa", "show", "@PROJECT.app"): ProcessAnswer(stdout=APP),
            ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", "main^{commit}"): ProcessAnswer(
                stdout=f"{MAIN_SHA}\n"
            ),
            ("awawa", "status", "--json", str(self.main_tree)): ProcessAnswer(stdout=CORPUS_STATUS),
            ("awawa", "show", "@TASK.T7"): ProcessAnswer(stdout=TASK_T7),
            ("awawa", "show", "@DECISION.D1"): ProcessAnswer(stdout=DECISION_D1),
            ("awawa", "show", "TASK"): ProcessAnswer(stdout="SCHEMA TASK\n\tFIELD TITLE\n"),
            ("awawa", "show", "TASK", "--json"): ProcessAnswer(stdout=TASK_SCHEMA),
            ("awawa", "show", "MILESTONE"): ProcessAnswer(exit_code=1),
        }
        self.runner = ScriptedProcessRunner(self.answers)
        self.runtime = create_test_runtime(
            create_test_paths(Path(self.root.name)), run_process=self.runner.run, resolve_plugin=resolve_forge
        )
        self.runtime.paths.config_root.mkdir(parents=True)
        self.runtime.paths.schema_file.write_text("SCHEMA REQUEST\n")
        self.runtime.paths.configuration_file.write_text("")

    def test_should_assemble_the_package_of_the_request_and_of_the_corpus_of_its_project(self):
        # Arrange
        request = argparse.Namespace(request="r1")

        # Act
        document = plan_context(request, self.runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "request": {"name": "r1", "project": "app", "text": "Let the tides be planned"},
                "corpus": str(self.main_tree),
                "status": [{"type": "TASK", "total": 2, "counts": {"draft": 1, "todo": 1}}],
                "decisions": [{"name": "D1", "title": "Tides run on the clock"}],
                "tasks": [{"name": "T7", "status": "draft", "title": "Ebb the tide"}],
                "schemas": {"TASK": "SCHEMA TASK\n\tFIELD TITLE\n"},
                "missing": [{"type": "MILESTONE"}, {"type": "TASK", "field": "MILESTONE"}],
                "next_task_number": 8,
                "anchors": {"brigade/tides.py": [{"entity": "@TASK.T7", "anchor": "brigade/tides.py::ebb"}]},
            },
        )

    def test_should_refuse_a_project_that_declares_no_corpus(self):
        # Arrange
        self.answers["awawa", "show", "@PROJECT.app"] = ProcessAnswer(stdout=APP_WITHOUT_CORPUS)
        request = argparse.Namespace(request="r1")

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            plan_context(request, self.runtime)

        # Assert
        self.assertEqual(str(refusal.exception), "@PROJECT.app declares no corpus")

    def test_should_read_the_corpus_of_the_main_branch_of_the_forge_on_github(self):
        # Arrange
        forge_tree = Path(self.root.name) / "cache" / "refs" / "app" / FORGE_MAIN_SHA
        forge_tree.mkdir(parents=True)
        self.answers["awawa", "show", "@PROJECT.app"] = ProcessAnswer(stdout=APP_ON_GITHUB)
        self.answers["git", "fetch", "--quiet", "origin", "main"] = ProcessAnswer()
        self.answers["git", "rev-parse", "--verify", "--quiet", "--end-of-options", "origin/main^{commit}"] = (
            ProcessAnswer(stdout=f"{FORGE_MAIN_SHA}\n")
        )
        self.answers["awawa", "status", "--json", str(forge_tree)] = ProcessAnswer(stdout=CORPUS_STATUS)
        request = argparse.Namespace(request="r1")

        # Act
        document = plan_context(request, self.runtime)

        # Assert
        self.assertEqual(document["corpus"], str(forge_tree))

    def test_should_fetch_the_main_branch_of_the_forge_before_reading_it_on_github(self):
        # Arrange
        self.answers["awawa", "show", "@PROJECT.app"] = ProcessAnswer(stdout=APP_ON_GITHUB)
        self.answers["git", "fetch", "--quiet", "origin", "main"] = ProcessAnswer()
        self.answers["git", "rev-parse", "--verify", "--quiet", "--end-of-options", "origin/main^{commit}"] = (
            ProcessAnswer(stdout=f"{MAIN_SHA}\n")
        )
        request = argparse.Namespace(request="r1")

        # Act
        plan_context(request, self.runtime)

        # Assert
        self.assertIn(("git", "fetch", "--quiet", "origin", "main"), self.runner.argvs)


class PlanContextRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_they_are(self):
        # Arrange
        options = argparse.Namespace(request="r1")

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertEqual(request, argparse.Namespace(request="r1"))


class PlanContextExitCodeTest(unittest.TestCase):
    def test_should_exit_0_once_the_package_is_assembled(self):
        # Arrange
        document = {"request": {"name": "r1"}}

        # Act
        exit_code = COMMAND.decide_exit_code(document)

        # Assert
        self.assertEqual(exit_code, 0)


class PlanContextTextTest(unittest.TestCase):
    def test_should_print_one_section_per_part_of_the_package(self):
        # Arrange
        document = {
            "request": {"name": "r1", "project": "app", "text": "Let the tides be planned"},
            "corpus": "/srv/app",
            "status": [
                {"type": "TASK", "total": 12, "counts": {"draft": 1, "done": 11}},
                {"type": "DECISION", "total": 0, "counts": {}},
            ],
            "decisions": [{"name": "D1", "title": "Tides run on the clock"}],
            "tasks": [{"name": "T7", "status": "draft", "title": "Ebb the tide"}],
            "schemas": {"TASK": "SCHEMA TASK\n\tFIELD TITLE\n"},
            "missing": [{"type": "MILESTONE"}, {"type": "TASK", "field": "MILESTONE"}],
            "next_task_number": 8,
            "anchors": {"brigade/tides.py": [{"entity": "@TASK.T7", "anchor": "brigade/tides.py::ebb"}]},
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "@REQUEST.r1 of @PROJECT.app\nLet the tides be planned\n"
            "\n"
            "Corpus /srv/app\nTASK      12  draft 1, done 11\nDECISION  0\n"
            "\n"
            "Active decisions\n@DECISION.D1  Tides run on the clock\n"
            "\n"
            "Draft and todo tasks\n@TASK.T7  draft  Ebb the tide\n"
            "\n"
            "Next free task number 8\n"
            "\n"
            "Anchors by file\nbrigade/tides.py\n  @TASK.T7  brigade/tides.py::ebb\n"
            "\n"
            "Missing schema MILESTONE\n"
            "\n"
            "Missing field MILESTONE of schema TASK\n"
            "\n"
            "SCHEMA TASK\n\tFIELD TITLE",
        )

    def test_should_print_each_schema_in_a_section_of_its_own(self):
        # Arrange
        document = {
            "request": {"name": "r1", "project": "app", "text": "Let the tides be planned"},
            "corpus": "/srv/app",
            "status": [{"type": "TASK", "total": 1, "counts": {"draft": 1}}],
            "decisions": [],
            "tasks": [{"name": "T7", "status": "draft", "title": "Ebb the tide"}],
            "schemas": {"TASK": "SCHEMA TASK\n\tFIELD TITLE\n", "MILESTONE": "SCHEMA MILESTONE\n\tFIELD TITLE\n"},
            "missing": [],
            "next_task_number": 8,
            "anchors": {},
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "@REQUEST.r1 of @PROJECT.app\nLet the tides be planned\n"
            "\n"
            "Corpus /srv/app\nTASK  1  draft 1\n"
            "\n"
            "Active decisions\n"
            "\n"
            "Draft and todo tasks\n@TASK.T7  draft  Ebb the tide\n"
            "\n"
            "Next free task number 8\n"
            "\n"
            "Anchors by file\n"
            "\n"
            "SCHEMA TASK\n\tFIELD TITLE\n"
            "\n"
            "SCHEMA MILESTONE\n\tFIELD TITLE",
        )

    def test_should_print_the_empty_inventory_of_a_corpus_without_schemas(self):
        # Arrange
        document = {
            "request": {"name": "r1", "project": "app", "text": "Let the tides be planned"},
            "corpus": "/srv/app",
            "status": [],
            "decisions": [],
            "tasks": [],
            "schemas": {},
            "missing": [{"type": "TASK"}, {"type": "MILESTONE"}],
            "next_task_number": 1,
            "anchors": {},
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "@REQUEST.r1 of @PROJECT.app\nLet the tides be planned\n"
            "\n"
            "Corpus /srv/app\n"
            "\n"
            "Active decisions\n"
            "\n"
            "Draft and todo tasks\n"
            "\n"
            "Next free task number 1\n"
            "\n"
            "Anchors by file\n"
            "\n"
            "Missing schema TASK\n"
            "\n"
            "Missing schema MILESTONE",
        )
