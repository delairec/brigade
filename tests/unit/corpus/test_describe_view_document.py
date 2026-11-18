import unittest
from pathlib import Path

from brigade.corpus.corpus_reader import CorpusReader
from brigade.corpus.describe_view_document import ViewRequest, describe_view_document
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import ScriptedProcessRunner
from tests.unit.corpus.awawa_corpus_double import (
    STRING,
    FakeCorpus,
    FakeEntity,
    create_awawa_double,
    declare_field,
    declare_literals,
    declare_reference,
)

ROOT = Path("/cache/refs/app/de446f3")
NO_IDE_LINK = ""
NO_FILTER = ()
TASK_SCHEMA = [
    declare_field("TITLE", STRING, required=True),
    declare_field("STATUS", *declare_literals("draft", "todo", "implemented", "archived"), required=True),
    declare_field("MILESTONE", declare_reference("MILESTONE")),
    declare_field("ROLE", *declare_literals("ada", "lex", "max"), repeatable=True),
    declare_field("COMPONENT", STRING),
    declare_field("AFTER", declare_reference("TASK"), repeatable=True),
]
MILESTONE_SCHEMA = [
    declare_field("TITLE", STRING, required=True),
    declare_field("STATUS", *declare_literals("planned", "active", "reached"), required=True),
]
DECISION_SCHEMA = [
    declare_field("TITLE", STRING),
    declare_field("STATUS", *declare_literals("active", "archived"), required=True),
]
SCHEMAS = {"TASK": TASK_SCHEMA, "MILESTONE": MILESTONE_SCHEMA, "DECISION": DECISION_SCHEMA}


def create_reader(corpus: FakeCorpus) -> CorpusReader:
    return CorpusReader(create_awawa_double(corpus, ROOT), ROOT, NO_IDE_LINK)


def describe(corpus: FakeCorpus, view: str, **request) -> dict:
    return describe_view_document(create_reader(corpus), ViewRequest(view=view, **request))


TREE_CORPUS = FakeCorpus(
    entities=(
        FakeEntity("SCHEMA", "TASK", None, file="corpus/_schema.awawa"),
        FakeEntity("MILESTONE", "M18", "active", (("TITLE", ('"Dashboard"',)),), file="corpus/m.awawa"),
        FakeEntity("DECISION", "TheTabIsRead", "active"),
        FakeEntity("DECISION", "TheBoardIsRead", "archived", line=4),
        FakeEntity("OPEN_QUESTION", "WhereTheTabIsServed", None, file="corpus/questions.awawa"),
        FakeEntity("OPEN_QUESTION", "WhoReadsTheTab", "open", file="corpus/questions.awawa", line=5),
        FakeEntity("TASK", "B10", "implemented", (("TITLE", ('"Read the corpus"',)),), line=10),
        FakeEntity("TASK", "B12", "todo", line=12),
        FakeEntity("TASK", "B2", "todo", (("TITLE", ('"Draw the board"',)),), line=2),
        FakeEntity("TASK", "B3", "archived", (("TITLE", ('"Draw the old view"',)),), line=3),
        FakeEntity("TASK", "B4", "draft", (("TITLE", ('"Draw the tree"',)),), line=4),
        FakeEntity("TASK", "B5", None, (("TITLE", ('"Draw nothing"',)),), line=5),
        FakeEntity("TASK", "B6", "done", line=6),
    ),
    schemas=SCHEMAS,
)


class DescribeTreeViewTest(unittest.TestCase):
    def test_should_order_the_types_by_the_statuses_they_use_and_set_the_schema_apart(self):
        # Act
        document = describe(TREE_CORPUS, "tree")

        # Assert
        self.assertEqual(document["domain"][0]["type"], "TASK")
        self.assertEqual(document["domain"][1]["type"], "DECISION")
        self.assertEqual(document["domain"][2]["type"], "MILESTONE")
        self.assertEqual(document["domain"][3]["type"], "OPEN_QUESTION")
        self.assertEqual(len(document["domain"]), 4)
        self.assertEqual(document["schema"][0]["type"], "SCHEMA")

    def test_should_group_the_tasks_in_the_order_of_their_lifecycle_and_collapse_the_last_one(self):
        # Act
        document = describe(TREE_CORPUS, "tree")

        # Assert
        groups = document["domain"][0]["groups"]
        self.assertEqual(groups[0]["status"], "draft")
        self.assertEqual(groups[1]["status"], "todo")
        self.assertEqual(groups[2]["status"], "implemented")
        self.assertEqual(groups[3]["status"], "archived")
        self.assertTrue(groups[3]["collapsed"])
        self.assertFalse(groups[2]["collapsed"])
        self.assertIsNone(groups[5]["status"])
        self.assertEqual(groups[5]["entities"][0]["code"], "B5")

    def test_should_list_the_entities_of_a_group_in_natural_order(self):
        # Act
        document = describe(TREE_CORPUS, "tree")

        # Assert
        self.assertEqual(document["domain"][0]["groups"][1]["entities"][0]["code"], "B2")
        self.assertEqual(document["domain"][0]["groups"][1]["entities"][1]["code"], "B12")

    def test_should_group_a_status_outside_the_lifecycle_after_the_lifecycle(self):
        # Act
        document = describe(TREE_CORPUS, "tree")

        # Assert
        self.assertEqual(document["domain"][0]["groups"][4]["status"], "done")

    def test_should_filter_the_entities_of_the_type_in_view_alone(self):
        # Act
        document = describe(TREE_CORPUS, "tree", entity_type="TASK", filters=("STATUS=todo",))

        # Assert
        self.assertEqual(document["domain"][0]["groups"][0]["entities"][1]["code"], "B12")
        self.assertEqual(len(document["domain"][0]["groups"]), 1)
        self.assertEqual(document["domain"][1]["type"], "DECISION")

    def test_should_list_the_entities_of_a_type_without_statuses_ungrouped(self):
        # Act
        document = describe(TREE_CORPUS, "tree")

        # Assert
        self.assertEqual(document["schema"][0]["entities"][0]["target"], "@SCHEMA.TASK")

    def test_should_keep_the_entities_whose_label_carries_the_search_case_aside(self):
        # Act
        document = describe(TREE_CORPUS, "tree", search="THE BOARD")

        # Assert
        self.assertEqual(document["domain"][0]["groups"][0]["entities"][0]["code"], "B2")
        self.assertEqual(len(document["domain"][0]["groups"]), 1)
        self.assertEqual(document["domain"][1]["groups"][0]["entities"][0]["code"], "TheBoardIsRead")


BOARD_CORPUS = FakeCorpus(
    entities=(
        FakeEntity("MILESTONE", "M17", "reached", (("TITLE", ('"Orders"',)),), file="corpus/m.awawa"),
        FakeEntity("MILESTONE", "M18", "active", (("TITLE", ('"Dashboard"',)),), file="corpus/m.awawa", line=5),
        FakeEntity("TASK", "B1", "implemented", (("COMPONENT", ('"corpus"',)), ("MILESTONE", ("@MILESTONE.M17",)))),
        FakeEntity(
            "TASK",
            "B2",
            "todo",
            (("COMPONENT", ('"corpus"',)), ("MILESTONE", ("@MILESTONE.M18",)), ("MILESTONE", ("@MILESTONE.M18",))),
        ),
        FakeEntity("TASK", "B3", "todo", (("COMPONENT", ('"tick"',)), ("ROLE", ("ada",)), ("ROLE", ("lex",)))),
        FakeEntity("TASK", "B4", "todo", (("COMPONENT", ('"tick"',)), ("ROLE", ("bilal",)))),
        FakeEntity("TASK", "B5", "draft", (("COMPONENT", ('"wave"',)),)),
        FakeEntity("TASK", "B6", "draft", (("COMPONENT", ('"inbox"',)),)),
        FakeEntity("TASK", "B7", "draft", (("COMPONENT", ('"ledger"',)),)),
        FakeEntity("TASK", "B8", "draft", (("COMPONENT", ('"serve"',)),)),
        FakeEntity("TASK", "B9", "draft", (("COMPONENT", ('"git"',)),)),
        FakeEntity("TASK", "B10", "draft"),
        FakeEntity("TASK", "B11", "draft", (("MILESTONE", ("@MILESTONE.M99",)),)),
    ),
    schemas=SCHEMAS,
)


class DescribeBoardViewTest(unittest.TestCase):
    def test_should_lay_one_column_per_status_the_schema_admits_in_schema_order(self):
        # Act
        document = describe(BOARD_CORPUS, "board", entity_type="TASK")

        # Assert
        self.assertEqual(document["field"], "STATUS")
        self.assertEqual(document["columns"][0]["label"], "draft")
        self.assertEqual(document["columns"][1]["label"], "todo")
        self.assertEqual(document["columns"][2]["entities"][0]["code"], "B1")
        self.assertEqual(document["columns"][3], {"label": "archived", "value": "archived", "entities": []})
        self.assertEqual(len(document["columns"]), 4)

    def test_should_lay_the_five_most_frequent_values_and_share_the_others_in_one_column(self):
        # Act
        document = describe(BOARD_CORPUS, "board", entity_type="TASK", field="COMPONENT")

        # Assert
        self.assertEqual(document["columns"][0]["label"], "corpus")
        self.assertEqual(document["columns"][1]["label"], "git")
        self.assertEqual(document["columns"][2]["label"], "inbox")
        self.assertEqual(document["columns"][3]["label"], "ledger")
        self.assertEqual(document["columns"][4]["label"], "tick")
        self.assertEqual(document["columns"][5]["label"], "Others (2)")
        self.assertEqual(document["columns"][5]["entities"][0]["code"], "B5")
        self.assertEqual(document["columns"][5]["entities"][0]["value"], "wave")
        self.assertEqual(document["columns"][5]["entities"][1]["value"], "serve")
        self.assertEqual(document["columns"][6]["label"], "(none)")
        self.assertEqual(document["columns"][6]["entities"][0]["code"], "B10")

    def test_should_lay_an_entity_holding_several_values_in_the_column_of_each(self):
        # Act
        document = describe(BOARD_CORPUS, "board", entity_type="TASK", field="ROLE")

        # Assert
        self.assertEqual(document["columns"][0]["entities"][0]["code"], "B3")
        self.assertEqual(document["columns"][1]["entities"][0]["code"], "B3")
        self.assertEqual(document["columns"][2], {"label": "max", "value": "max", "entities": []})
        self.assertEqual(document["columns"][3]["label"], "bilal")

    def test_should_lay_every_entity_under_none_for_a_field_the_type_does_not_declare(self):
        # Act
        document = describe(BOARD_CORPUS, "board", entity_type="TASK", field="UNDECLARED")

        # Assert
        self.assertEqual(document["columns"][0]["label"], "(none)")
        self.assertEqual(len(document["columns"]), 1)

    def test_should_keep_the_tasks_whose_milestone_stands_at_the_status_filtered(self):
        # Act
        document = describe(
            BOARD_CORPUS, "board", entity_type="TASK", field="MILESTONE", filters=("MILESTONE.STATUS=active",)
        )

        # Assert
        self.assertEqual(document["columns"][0]["value"], "@MILESTONE.M18")
        self.assertEqual(document["columns"][0]["label"], "M18")
        self.assertEqual(document["columns"][0]["entities"][0]["code"], "B2")
        self.assertEqual(len(document["columns"]), 1)

    def test_should_keep_the_entities_holding_one_of_the_values_given_for_a_field(self):
        # Act
        document = describe(BOARD_CORPUS, "board", entity_type="TASK", filters=("STATUS=implemented", "STATUS=todo"))

        # Assert
        self.assertEqual(document["columns"][0]["entities"], [])
        self.assertEqual(document["columns"][1]["entities"][2]["code"], "B4")
        self.assertEqual(document["columns"][2]["entities"][0]["code"], "B1")

    def test_should_refuse_a_board_without_a_type(self):
        # Act
        with self.assertRaises(BrigadeError) as raised:
            describe(BOARD_CORPUS, "board")

        # Assert
        self.assertEqual(str(raised.exception), "--view board reads the entities of --type")

    def test_should_refuse_a_filter_without_a_value(self):
        # Act
        with self.assertRaises(BrigadeError) as raised:
            describe(BOARD_CORPUS, "board", entity_type="TASK", filters=("STATUS",))

        # Assert
        self.assertEqual(str(raised.exception), "--filter takes <field>=<value>, given STATUS")


DEPENDENCIES_CORPUS = FakeCorpus(
    entities=(
        FakeEntity("TASK", "B1", "implemented"),
        FakeEntity("TASK", "B2", "todo", (("AFTER", ("@TASK.B1",)), ("AFTER", ("@TASK.B1",)))),
        FakeEntity("TASK", "B3", "todo", (("AFTER", ("@TASK.B2",)), ("AFTER", ("@TASK.B4",)))),
        FakeEntity("TASK", "B4", "todo", (("AFTER", ("@TASK.B3",)),)),
        FakeEntity("TASK", "B5", "draft", (("AFTER", ("@TASK.B6",)),)),
        FakeEntity("TASK", "B6", "draft", (("AFTER", ("@TASK.B5",)),)),
        FakeEntity("TASK", "B7", "draft", (("AFTER", ("@TASK.B5",)),)),
    ),
    schemas=SCHEMAS,
)


class DescribeDependenciesViewTest(unittest.TestCase):
    def test_should_root_the_entities_that_wait_on_nothing_through_the_field_referring_to_their_type(self):
        # Act
        document = describe(DEPENDENCIES_CORPUS, "dependencies", entity_type="TASK")

        # Assert
        self.assertEqual(document["field"], "AFTER")
        self.assertEqual(document["roots"][0]["code"], "B1")
        self.assertEqual(document["roots"][0]["dependents"][0]["code"], "B2")
        self.assertEqual(len(document["roots"][0]["dependents"]), 1)
        self.assertFalse(document["roots"][0]["in_cycle"])

    def test_should_flag_an_entity_in_a_cycle_and_stop_at_one_met_again_along_its_path(self):
        # Act
        document = describe(DEPENDENCIES_CORPUS, "dependencies", entity_type="TASK")

        # Assert
        b3 = document["roots"][0]["dependents"][0]["dependents"][0]
        b4 = b3["dependents"][0]
        self.assertTrue(b3["in_cycle"])
        self.assertFalse(b3["already_above"])
        self.assertEqual(b4["code"], "B4")
        self.assertEqual(b4["dependents"][0]["code"], "B3")
        self.assertTrue(b4["dependents"][0]["already_above"])
        self.assertEqual(b4["dependents"][0]["dependents"], [])

    def test_should_give_a_root_of_its_own_to_a_cycle_no_root_reaches(self):
        # Act
        document = describe(DEPENDENCIES_CORPUS, "dependencies", entity_type="TASK")

        # Assert
        self.assertEqual(document["roots"][1]["code"], "B5")
        self.assertTrue(document["roots"][1]["in_cycle"])
        self.assertEqual(document["roots"][1]["dependents"][0]["code"], "B6")
        self.assertEqual(len(document["roots"]), 2)

    def test_should_root_an_entity_whose_prerequisites_are_all_filtered_out(self):
        # Act
        document = describe(DEPENDENCIES_CORPUS, "dependencies", entity_type="TASK", filters=("STATUS=todo",))

        # Assert
        self.assertEqual(document["roots"][0]["code"], "B2")
        self.assertEqual(len(document["roots"]), 1)

    def test_should_read_the_dependencies_through_the_field_given(self):
        # Act
        document = describe(TREE_CORPUS, "dependencies", entity_type="MILESTONE", field="AFTER")

        # Assert
        self.assertEqual(document["field"], "AFTER")
        self.assertEqual(document["roots"][0]["code"], "M18")

    def test_should_refuse_a_type_with_no_field_referring_to_its_own_entities(self):
        # Act
        with self.assertRaises(BrigadeError) as raised:
            describe(TREE_CORPUS, "dependencies", entity_type="MILESTONE")

        # Assert
        self.assertEqual(str(raised.exception), "MILESTONE has no field referring to entities of its own type")


HEALTH_CORPUS = FakeCorpus(
    entities=(
        FakeEntity("TASK", "B1", "todo", (("TITLE", ('"Read the corpus"',)),)),
        FakeEntity("TASK", "B2", "todo", (("TITLE", ('"Draw the board"',)),), line=9),
        FakeEntity("TASK", "?", None, line=30),
    ),
    schemas=SCHEMAS,
    diagnostics=(
        {
            "rule": "L003",
            "severity": "warning",
            "file": "corpus/tasks.awawa",
            "line": 3,
            "message": "field FOO is not declared on TASK",
            "entity": {"type": "TASK", "name": "B1"},
        },
        {
            "rule": "L007",
            "severity": "warning",
            "file": "corpus/tasks.awawa",
            "line": 12,
            "message": "field STATUS expects draft|todo|implemented|archived, given done",
            "entity": {"type": "TASK", "name": "B2"},
        },
        {
            "rule": "L002",
            "severity": "error",
            "file": "corpus/tasks.awawa",
            "line": 10,
            "message": "field TITLE is required",
            "entity": {"type": "TASK", "name": "B2"},
        },
        {
            "rule": "L022",
            "severity": "error",
            "file": "corpus/_schema.awawa",
            "line": 1,
            "message": "SCHEMA TASK has no DESC",
            "entity": None,
        },
        {
            "rule": "L001",
            "severity": "warning",
            "file": "corpus/0.awawa",
            "line": 30,
            "message": "the name of TASK cannot be read",
            "entity": {"type": "TASK", "name": "?"},
        },
    ),
    unresolved=1,
)


class DescribeHealthViewTest(unittest.TestCase):
    def test_should_count_the_errors_the_warnings_and_the_unresolved_references(self):
        # Act
        document = describe(HEALTH_CORPUS, "health")

        # Assert
        self.assertEqual(document["errors"], 2)
        self.assertEqual(document["warnings"], 3)
        self.assertEqual(document["unresolved"], 1)

    def test_should_gather_the_diagnostics_per_entity_the_entities_with_the_most_errors_first(self):
        # Act
        document = describe(HEALTH_CORPUS, "health")

        # Assert
        self.assertEqual(document["entities"][0]["entity"]["code"], "B2")
        self.assertEqual(
            document["entities"][0]["diagnostics"],
            [
                {
                    "rule": "L002",
                    "severity": "error",
                    "file": "corpus/tasks.awawa",
                    "line": 10,
                    "message": "field TITLE is required",
                },
                {
                    "rule": "L007",
                    "severity": "warning",
                    "file": "corpus/tasks.awawa",
                    "line": 12,
                    "message": "field STATUS expects draft|todo|implemented|archived, given done",
                },
            ],
        )
        self.assertEqual(document["entities"][1]["entity"]["code"], "B1")

    def test_should_gather_the_diagnostics_on_no_entity_under_their_file(self):
        # Act
        document = describe(HEALTH_CORPUS, "health")

        # Assert
        self.assertEqual(
            document["files"],
            [
                {
                    "file": "corpus/_schema.awawa",
                    "diagnostics": [
                        {
                            "rule": "L022",
                            "severity": "error",
                            "file": "corpus/_schema.awawa",
                            "line": 1,
                            "message": "SCHEMA TASK has no DESC",
                        }
                    ],
                },
                {
                    "file": "corpus/0.awawa",
                    "diagnostics": [
                        {
                            "rule": "L001",
                            "severity": "warning",
                            "file": "corpus/0.awawa",
                            "line": 30,
                            "message": "the name of TASK cannot be read",
                        }
                    ],
                },
            ],
        )

    def test_should_narrow_the_diagnostics_by_the_search_and_leave_the_filters_aside(self):
        # Act
        document = describe(HEALTH_CORPUS, "health", search="not declared", filters=("STATUS=draft",))

        # Assert
        self.assertEqual(document["entities"][0]["entity"]["code"], "B1")
        self.assertEqual(len(document["entities"]), 1)
        self.assertEqual(document["files"], [])


class DescribeEntityDetailTest(unittest.TestCase):
    def test_should_add_the_entity_what_it_refers_to_and_what_refers_to_it(self):
        # Act
        document = describe(BOARD_CORPUS, "board", entity_type="TASK", entity="@MILESTONE.M18")

        # Assert
        self.assertEqual(
            document["detail"],
            {
                "entity": {
                    "type": "MILESTONE",
                    "name": "M18",
                    "target": "@MILESTONE.M18",
                    "file": "/cache/refs/app/de446f3/corpus/m.awawa",
                    "line": 5,
                    "status": "active",
                    "fields": [
                        {"name": "STATUS", "atoms": ["active"], "fields": []},
                        {"name": "TITLE", "atoms": ['"Dashboard"'], "fields": []},
                    ],
                },
                "references": [],
                "referenced_by": [{"target": "@TASK.B2", "code": "B2", "label": "B2", "status": "todo"}],
            },
        )

    def test_should_describe_the_entities_the_entity_refers_to(self):
        # Act
        document = describe(BOARD_CORPUS, "board", entity_type="TASK", entity="@TASK.B1")

        # Assert
        self.assertEqual(
            document["detail"]["references"],
            [{"target": "@MILESTONE.M17", "code": "M17", "label": "Orders", "status": "reached"}],
        )


class ReadTheCorpusThroughAwawaTest(unittest.TestCase):
    def test_should_read_the_schema_of_a_type_from_the_context_of_its_first_entity(self):
        # Arrange
        runner = ScriptedProcessRunner({}, fallback=create_awawa_double(TREE_CORPUS, ROOT))
        reader = CorpusReader(runner.run, ROOT, NO_IDE_LINK)

        # Act
        describe_view_document(reader, ViewRequest(view="tree", filters=NO_FILTER))

        # Assert
        self.assertIn(
            ("awawa", "context", "@TASK.B10", "--depth", "0", "--with-schema", "--json", str(ROOT)), runner.argvs
        )
