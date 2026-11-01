import json
import unittest
from pathlib import Path

from brigade.corpus.describe_corpus_view import CorpusView, describe_corpus_view
from brigade.errors import CommandFailed
from tests.unit.commands.command_runtime import ProcessAnswer, ScriptedProcessRunner

ROOT = Path("/cache/refs/oak/de446f3")
TASKS_FILE = "/cache/refs/oak/de446f3/corpus/tasks.awawa"
IDE_LINK = "idea://open?file={path}&line={line}"
STATUS_OF_THE_CORPUS = json.dumps(
    {
        "types": [{"type": "MILESTONE"}, {"type": "TASK"}],
        "entities": [
            {"type": "MILESTONE", "name": "M3", "target": "@MILESTONE.M3", "file": "/m.awawa", "line": 1},
            {"type": "TASK", "name": "B30", "target": "@TASK.B30", "file": TASKS_FILE, "line": 40, "status": "todo"},
            {
                "type": "TASK",
                "name": "B27",
                "target": "@TASK.B27",
                "file": TASKS_FILE,
                "line": 12,
                "status": "implemented",
            },
            {"type": "TASK", "name": "?", "target": "@TASK.?", "file": TASKS_FILE, "line": 90, "status": None},
        ],
    }
)
B27_SHOWN = json.dumps({"fields": [{"name": "STATUS", "atoms": ["implemented"]}]})
B30_SHOWN = json.dumps({"fields": [{"name": "STATUS", "atoms": ["todo"]}]})
B30_CONTEXT = json.dumps(
    {
        "entities": [
            {"type": "TASK", "name": "B30", "file": TASKS_FILE, "line": 40, "status": "todo", "depth": 0},
            {"type": "TASK", "name": "B27", "file": TASKS_FILE, "line": 12, "status": "implemented", "depth": 1},
        ],
        "referenced_by": [
            {"type": "TASK", "name": "B32", "target": "@TASK.B30", "converse": "BEFORE"},
            {"type": "TASK", "name": "B32", "target": "@TASK.B30", "converse": None},
            {"type": "TASK", "name": "B29", "target": "@MILESTONE.M3", "converse": "COMPRISES"},
        ],
    }
)


def create_corpus_runner(**answers: ProcessAnswer) -> ScriptedProcessRunner:
    return ScriptedProcessRunner(
        {
            ("awawa", "status", "--json", str(ROOT)): ProcessAnswer(stdout=STATUS_OF_THE_CORPUS),
            ("awawa", "show", "@TASK.B27", "--json", str(ROOT)): ProcessAnswer(stdout=B27_SHOWN),
            ("awawa", "show", "@TASK.B30", "--json", str(ROOT)): ProcessAnswer(stdout=B30_SHOWN),
            ("awawa", "context", "@TASK.B30", "--depth", "1", "--json", str(ROOT)): ProcessAnswer(stdout=B30_CONTEXT),
            **answers,
        }
    )


class DescribeCorpusViewWithoutATypeTest(unittest.TestCase):
    def test_should_list_the_entity_types_of_the_corpus_alone(self):
        # Arrange
        view = CorpusView(entity_type=None)

        # Act
        document = describe_corpus_view(create_corpus_runner().run, ROOT, view)

        # Assert
        self.assertEqual(document, {"types": ["MILESTONE", "TASK"]})


class DescribeCorpusViewOfATypeTest(unittest.TestCase):
    def test_should_list_the_entities_of_the_type_with_the_link_to_their_line(self):
        # Arrange
        view = CorpusView(entity_type="TASK", ide_link=IDE_LINK)

        # Act
        document = describe_corpus_view(create_corpus_runner().run, ROOT, view)

        # Assert
        self.assertEqual(
            document,
            {
                "type": "TASK",
                "types": ["MILESTONE", "TASK"],
                "entities": [
                    {
                        "target": "@TASK.B27",
                        "status": "implemented",
                        "file": "corpus/tasks.awawa",
                        "line": 12,
                        "ide_link": "idea://open?file=/cache/refs/oak/de446f3/corpus/tasks.awawa&line=12",
                    },
                    {
                        "target": "@TASK.B30",
                        "status": "todo",
                        "file": "corpus/tasks.awawa",
                        "line": 40,
                        "ide_link": "idea://open?file=/cache/refs/oak/de446f3/corpus/tasks.awawa&line=40",
                    },
                ],
            },
        )

    def test_should_carry_no_link_to_the_line_when_the_ide_link_is_empty(self):
        # Arrange
        no_ide_link = ""
        view = CorpusView(entity_type="TASK", ide_link=no_ide_link)

        # Act
        document = describe_corpus_view(create_corpus_runner().run, ROOT, view)

        # Assert
        self.assertIsNone(document["entities"][0]["ide_link"])


class DescribeCorpusViewOfABoardTest(unittest.TestCase):
    def test_should_place_every_task_under_its_status(self):
        # Arrange
        view = CorpusView(entity_type="TASK", field="STATUS")

        # Act
        document = describe_corpus_view(create_corpus_runner().run, ROOT, view)

        # Assert
        self.assertEqual(document["field"], "STATUS")
        self.assertEqual(
            document["board"],
            [{"value": "implemented", "targets": ["@TASK.B27"]}, {"value": "todo", "targets": ["@TASK.B30"]}],
        )

    def test_should_place_an_entity_without_the_field_in_a_column_of_its_own(self):
        # Arrange
        b30_without_milestone = ProcessAnswer(stdout=json.dumps({"fields": []}))
        b27_in_m3 = ProcessAnswer(stdout=json.dumps({"fields": [{"name": "MILESTONE", "atoms": ["@MILESTONE.M3"]}]}))
        runner = create_corpus_runner()
        runner.answers[("awawa", "show", "@TASK.B30", "--json", str(ROOT))] = b30_without_milestone
        runner.answers[("awawa", "show", "@TASK.B27", "--json", str(ROOT))] = b27_in_m3
        view = CorpusView(entity_type="TASK", field="MILESTONE")

        # Act
        document = describe_corpus_view(runner.run, ROOT, view)

        # Assert
        self.assertEqual(
            document["board"],
            [{"value": "@MILESTONE.M3", "targets": ["@TASK.B27"]}, {"value": None, "targets": ["@TASK.B30"]}],
        )


class DescribeCorpusViewOfAnEntityTest(unittest.TestCase):
    def test_should_list_what_the_entity_reaches_and_what_references_it(self):
        # Arrange
        view = CorpusView(entity_type="TASK", entity="@TASK.B30", ide_link=IDE_LINK)

        # Act
        document = describe_corpus_view(create_corpus_runner().run, ROOT, view)

        # Assert
        self.assertEqual(
            document["dependencies"],
            {
                "entity": "@TASK.B30",
                "reaches": [
                    {
                        "target": "@TASK.B27",
                        "status": "implemented",
                        "file": "corpus/tasks.awawa",
                        "line": 12,
                        "ide_link": "idea://open?file=/cache/refs/oak/de446f3/corpus/tasks.awawa&line=12",
                    }
                ],
                "referenced_by": ["@TASK.B32"],
            },
        )

    def test_should_refuse_an_entity_the_corpus_does_not_define(self):
        # Arrange
        runner = create_corpus_runner()
        runner.answers[("awawa", "context", "@TASK.B999")] = CommandFailed(
            ("awawa", "context", "@TASK.B999"), 1, "awawa context: @TASK.B999 is not defined in the workspace\n"
        )
        view = CorpusView(entity_type="TASK", entity="@TASK.B999")

        # Act
        with self.assertRaises(CommandFailed) as raised:
            describe_corpus_view(runner.run, ROOT, view)

        # Assert
        self.assertIn("@TASK.B999 is not defined in the workspace", str(raised.exception))
