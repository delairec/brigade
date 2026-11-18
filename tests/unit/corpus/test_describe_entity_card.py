import unittest
from pathlib import Path

from brigade.corpus.corpus_reader import CorpusReader
from brigade.corpus.describe_entity_card import describe_entity_card
from tests.unit.corpus.awawa_corpus_double import (
    STRING,
    UINT,
    FakeCorpus,
    FakeEntity,
    create_awawa_double,
    declare_field,
    declare_literals,
    declare_reference,
)

ROOT = Path("/cache/refs/app/de446f3")
IDE_LINK = "idea://open?file={path}&line={line}"
NO_IDE_LINK = ""
CORPUS = FakeCorpus(
    entities=(
        FakeEntity("MILESTONE", "M18", "active", (("TITLE", ('"User-friendly dashboard"',)),), file="corpus/m.awawa"),
        FakeEntity(
            "TASK",
            "B1",
            "implemented",
            (("TITLE", ('"Read the corpus"',)), ("MILESTONE", ("@MILESTONE.M18",)), ("DELIVERED_BY", ("12",))),
        ),
        FakeEntity(
            "TASK",
            "B2",
            "todo",
            (
                ("TITLE", ('"Draw the board"',)),
                ("TYPE", ("feat",)),
                ("MILESTONE", ("@MILESTONE.M18",)),
                ("ROLE", ("ada",)),
                ("ROLE", ("lex",)),
                ("SPEC", ('"the board is drawn"',)),
                ("AFTER", ("@TASK.B1",)),
                ("AFTER", ("@TASK.B3",)),
                ("DELIVERED_BY", ("30",)),
            ),
            line=9,
        ),
        FakeEntity(
            "TASK",
            "B3",
            "todo",
            (("TITLE", ('"Draw the tree"',)), ("AFTER", ("@TASK.B1",)), ("AFTER", ("@TASK.B99",))),
            line=20,
        ),
        FakeEntity("TASK", "B4", None, (("AFTER", ("@TASK.B1",)),), line=30),
        FakeEntity("TASK", "B5", "todo", (("AFTER", ("@TASK.B4",)),), line=40),
        FakeEntity(
            "DECISION",
            "TheTabIsReadOnly",
            "active",
            (("TITLE", ('"the tab is read only"',)), ("RULING", ('"the tab writes nothing"',))),
        ),
    ),
    schemas={
        "MILESTONE": [
            declare_field("TITLE", STRING, required=True),
            declare_field("STATUS", *declare_literals("planned", "active", "reached"), required=True),
        ],
        "TASK": [
            declare_field("TITLE", STRING, required=True),
            declare_field("STATUS", *declare_literals("draft", "todo", "implemented", "archived"), required=True),
            declare_field("TYPE", *declare_literals("feat", "fix")),
            declare_field("MILESTONE", declare_reference("MILESTONE"), required=True),
            declare_field("ROLE", *declare_literals("ada", "lex"), repeatable=True),
            declare_field("SPEC", STRING, required=True, repeatable=True),
            declare_field("AFTER", declare_reference("TASK"), repeatable=True),
            declare_field("DELIVERED_BY", UINT),
        ],
        "DECISION": [
            declare_field("TITLE", STRING),
            declare_field("STATUS", *declare_literals("active", "archived"), required=True),
            declare_field("RULING", STRING, required=True, repeatable=True),
        ],
    },
)


def create_reader(ide_link: str = IDE_LINK) -> CorpusReader:
    return CorpusReader(create_awawa_double(CORPUS, ROOT), ROOT, ide_link)


class DescribeEntityCardTest(unittest.TestCase):
    def test_should_present_the_task_with_its_title_and_its_first_four_facts(self):
        # Arrange
        reader = create_reader()

        # Act
        card = describe_entity_card(reader, reader.row("@TASK.B2"))

        # Assert
        self.assertEqual(
            card,
            {
                "type": "TASK",
                "target": "@TASK.B2",
                "code": "B2",
                "label": "Draw the board",
                "facts": [
                    {"field": "TYPE", "values": [{"text": "feat", "target": None, "status": None}]},
                    {
                        "field": "MILESTONE",
                        "values": [{"text": "M18", "target": "@MILESTONE.M18", "status": "active"}],
                    },
                    {
                        "field": "ROLE",
                        "values": [
                            {"text": "ada", "target": None, "status": None},
                            {"text": "lex", "target": None, "status": None},
                        ],
                    },
                    {
                        "field": "AFTER",
                        "values": [
                            {"text": "B1", "target": "@TASK.B1", "status": "implemented"},
                            {"text": "B3", "target": "@TASK.B3", "status": "todo"},
                        ],
                    },
                ],
                "status": "todo",
                "position": 1,
                "waiting": True,
                "file": "corpus/tasks.awawa",
                "line": 9,
                "ide_link": "idea://open?file=/cache/refs/app/de446f3/corpus/tasks.awawa&line=9",
            },
        )

    def test_should_label_an_entity_whose_type_requires_no_single_string_by_its_name_read_as_a_sentence(self):
        # Arrange
        reader = create_reader()

        # Act
        card = describe_entity_card(reader, reader.row("@DECISION.TheTabIsReadOnly"))

        # Assert
        self.assertEqual(card["label"], "The tab is read only")

    def test_should_not_wait_on_an_entity_further_along_the_lifecycle(self):
        # Arrange
        reader = create_reader()

        # Act
        card = describe_entity_card(reader, reader.row("@TASK.B3"))

        # Assert
        self.assertFalse(card["waiting"])

    def test_should_not_wait_on_an_entity_of_another_type(self):
        # Arrange
        reader = create_reader()

        # Act
        card = describe_entity_card(reader, reader.row("@TASK.B1"))

        # Assert
        self.assertFalse(card["waiting"])

    def test_should_not_wait_when_the_entity_stands_at_no_status(self):
        # Arrange
        reader = create_reader()

        # Act
        card = describe_entity_card(reader, reader.row("@TASK.B4"))

        # Assert
        self.assertFalse(card["waiting"])

    def test_should_wait_on_an_entity_of_its_type_standing_at_no_status(self):
        # Arrange
        reader = create_reader()

        # Act
        card = describe_entity_card(reader, reader.row("@TASK.B5"))

        # Assert
        self.assertTrue(card["waiting"])

    def test_should_carry_no_link_to_the_line_when_the_configuration_sets_none(self):
        # Arrange
        reader = create_reader(NO_IDE_LINK)

        # Act
        card = describe_entity_card(reader, reader.row("@TASK.B3"))

        # Assert
        self.assertIsNone(card["ide_link"])
