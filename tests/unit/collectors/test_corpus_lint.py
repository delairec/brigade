import json

from brigade.collectors.corpus_lint import collect
from tests.unit.collectors.scan_fixtures import ENVIRONMENT_OF_OAK, ScanCollectorTestCase, create_equipment

LINT = ("awawa", "lint", "--strict", "--json", ".")
DIAGNOSTIC_OF_AN_ENTITY = {
    "rule": "L003",
    "severity": "error",
    "file": "./corpus/tasks.awawa",
    "line": 7,
    "message": "field BOGUS is not declared on TASK",
    "entity": {"type": "TASK", "name": "B1"},
}
DIAGNOSTIC_OF_NO_ENTITY = {
    "rule": "L012",
    "severity": "error",
    "file": "./corpus/_schema.awawa",
    "line": 1,
    "message": "the schema declares no type",
    "entity": None,
}


class CorpusLintCollectorTest(ScanCollectorTestCase):
    def test_should_print_one_item_per_diagnostic_of_the_corpus_at_the_main_branch(self):
        # Arrange
        self.register_oak(("CORPUS", "corpus"))
        self.create_cached_tree_of_main()
        self.processes.answer(
            LINT, exit_code=1, stdout=json.dumps({"diagnostics": [DIAGNOSTIC_OF_AN_ENTITY, DIAGNOSTIC_OF_NO_ENTITY]})
        )

        # Act
        document = collect(ENVIRONMENT_OF_OAK, self.runtime, create_equipment(None))

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "collector": "corpus-lint",
                "collected_at": "2026-10-19T09:00:00Z",
                "cache": False,
                "summary": {"diagnostics": 2},
                "items": [
                    {
                        "rule": "L003",
                        "severity": "error",
                        "file": "corpus/tasks.awawa",
                        "line": 7,
                        "message": "field BOGUS is not declared on TASK",
                        "entity": {"type": "TASK", "name": "B1"},
                        "fingerprint": "L003:corpus/tasks.awawa:TASK.B1",
                    },
                    {
                        "rule": "L012",
                        "severity": "error",
                        "file": "corpus/_schema.awawa",
                        "line": 1,
                        "message": "the schema declares no type",
                        "entity": None,
                        "fingerprint": "L012:corpus/_schema.awawa:none",
                    },
                ],
            },
        )

    def test_should_lint_the_checkout_of_the_main_branch_and_change_nothing(self):
        # Arrange
        self.register_oak(("CORPUS", "corpus"))
        self.create_cached_tree_of_main()
        self.processes.answer(LINT, stdout=json.dumps({"diagnostics": []}))

        # Act
        collect(ENVIRONMENT_OF_OAK, self.runtime, create_equipment(None))

        # Assert
        self.assertEqual(
            self.processes.list_argvs()[-2:],
            [
                ("git", "rev-parse", "--verify", "--quiet", "--end-of-options", "main^{commit}"),
                LINT,
            ],
        )

    def test_should_print_no_item_for_a_project_with_no_corpus(self):
        # Arrange
        self.register_oak()

        # Act
        document = collect(ENVIRONMENT_OF_OAK, self.runtime, create_equipment(None))

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "collector": "corpus-lint",
                "collected_at": "2026-10-19T09:00:00Z",
                "cache": False,
                "summary": {"diagnostics": 0},
                "items": [],
            },
        )
