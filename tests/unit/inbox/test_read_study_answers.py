import tempfile
import unittest
from pathlib import Path

from brigade.inbox.read_study_answers import read_study_answers
from tests.unit.commands.command_runtime import create_corpus_double, write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.reports.document_plugin_double import DocumentPluginDouble


class ReadStudyAnswersTest(unittest.TestCase):
    def test_should_read_each_study_answer_with_the_project_of_its_study(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(root)
        (root / "config" / "answers.awawa").write_text("", encoding="utf-8")
        plugin = DocumentPluginDouble(
            {
                str(root / "config" / "answers.awawa"): [
                    {
                        "type": "ANSWER",
                        "name": "health_20261018T090000Z_a1",
                        "fields": [{"name": "STUDY", "value": "health"}],
                    },
                    {
                        "type": "ANSWER",
                        "name": "disk_20261019T090000Z_b2",
                        "fields": [{"name": "STUDY", "value": "disk"}],
                    },
                ],
            }
        )
        studies = {
            "STUDY": {
                "health": (
                    ("TITLE", "the health of oak"),
                    ("PROJECT", "@PROJECT.oak"),
                    ("COLLECTOR", "ledger"),
                    ("SLOT", "none"),
                    ("OUTPUT", "entity:ANSWER"),
                    ("ANSWER", "ANSWER"),
                    ("STATUS", "active"),
                ),
                "disk": (
                    ("TITLE", "the disk of the machine"),
                    ("COLLECTOR", "shell: df"),
                    ("SLOT", "none"),
                    ("OUTPUT", "entity:ANSWER"),
                    ("ANSWER", "ANSWER"),
                    ("STATUS", "active"),
                ),
            }
        }
        runtime = create_test_runtime(create_test_paths(root), run_process=create_corpus_double(studies))

        # Act
        answers = read_study_answers(runtime, lambda: plugin)

        # Assert
        self.assertEqual(
            answers,
            [
                {
                    "id": "health_20261018T090000Z_a1",
                    "study": "health",
                    "project": "oak",
                    "type": "ANSWER",
                    "fields": [{"name": "STUDY", "value": "health"}],
                },
                {
                    "id": "disk_20261019T090000Z_b2",
                    "study": "disk",
                    "project": None,
                    "type": "ANSWER",
                    "fields": [{"name": "STUDY", "value": "disk"}],
                },
            ],
        )

    def test_should_find_none_where_the_operational_corpus_holds_no_answer(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(root)
        no_study = {}
        no_document = DocumentPluginDouble({})
        runtime = create_test_runtime(create_test_paths(root), run_process=create_corpus_double(no_study))

        # Act
        answers = read_study_answers(runtime, lambda: no_document)

        # Assert
        self.assertEqual(answers, [])
