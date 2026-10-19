import argparse
import json
import tempfile
import unittest
from pathlib import Path

from brigade.commands.plan_context import COMMAND, plan_context
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import ProcessAnswer, ScriptedProcessRunner, create_runtime

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
APP = json.dumps({"fields": [{"name": "PATH", "atoms": ['"/srv/app"']}, {"name": "CORPUS", "atoms": ['"corpus"']}]})
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
TASK_SCHEMA = json.dumps({"fields": [{"name": "FIELD", "atoms": ["TITLE"]}]})


class PlanContextTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.answers = {
            ("awawa", "show", "@REQUEST.r1"): ProcessAnswer(stdout=REQUEST),
            ("awawa", "status", "PROJECT"): ProcessAnswer(stdout=PROJECTS),
            ("awawa", "show", "@PROJECT.app"): ProcessAnswer(stdout=APP),
            ("awawa", "status", "--json", "/srv/app"): ProcessAnswer(stdout=CORPUS_STATUS),
            ("awawa", "show", "@TASK.T7"): ProcessAnswer(stdout=TASK_T7),
            ("awawa", "show", "@DECISION.D1"): ProcessAnswer(stdout=DECISION_D1),
            ("awawa", "show", "TASK"): ProcessAnswer(stdout="SCHEMA TASK\n\tFIELD TITLE\n"),
            ("awawa", "show", "TASK", "--json"): ProcessAnswer(stdout=TASK_SCHEMA),
            ("awawa", "show", "MILESTONE"): ProcessAnswer(exit_code=1),
        }
        self.runtime = create_runtime(Path(self.root.name), run_process=ScriptedProcessRunner(self.answers).run)
        self.runtime.paths.config_root.mkdir(parents=True)
        self.runtime.paths.schema_file.write_text("SCHEMA REQUEST\n")

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
                "corpus": "/srv/app",
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
