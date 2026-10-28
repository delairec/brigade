import tempfile
import unittest
from pathlib import Path

from brigade.reports.read_reports import read_reports
from tests.unit.commands.command_runtime import create_corpus_double, write_operational_corpus
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.reports.document_plugin_double import DocumentPluginDouble


class ReadReportsTest(unittest.TestCase):
    def test_should_read_the_wave_reports_then_the_study_answers_through_the_document_plugin(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(root)
        (root / "config" / "reports.awawa").write_text("", encoding="utf-8")
        (root / "config" / "answers.awawa").write_text("", encoding="utf-8")
        plugin = DocumentPluginDouble(
            {
                str(root / "config" / "reports.awawa"): [
                    {
                        "type": "REPORT",
                        "name": "oak_w3",
                        "fields": [{"name": "WAVE", "value": "oak_w3"}, {"name": "PROJECT", "value": "oak"}],
                    }
                ],
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
        reports = read_reports(runtime, plugin)

        # Assert
        self.assertEqual(
            reports,
            [
                {
                    "id": "oak_w3",
                    "kind": "wave-report",
                    "project": "oak",
                    "type": "REPORT",
                    "fields": [{"name": "WAVE", "value": "oak_w3"}, {"name": "PROJECT", "value": "oak"}],
                },
                {
                    "id": "health_20261018T090000Z_a1",
                    "kind": "study-answer",
                    "project": "oak",
                    "type": "ANSWER",
                    "fields": [{"name": "STUDY", "value": "health"}],
                },
                {
                    "id": "disk_20261019T090000Z_b2",
                    "kind": "study-answer",
                    "project": None,
                    "type": "ANSWER",
                    "fields": [{"name": "STUDY", "value": "disk"}],
                },
            ],
        )

    def test_should_find_none_where_the_operational_corpus_holds_no_report(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(root)
        no_study = {}
        no_document = DocumentPluginDouble({})
        runtime = create_test_runtime(create_test_paths(root), run_process=create_corpus_double(no_study))

        # Act
        reports = read_reports(runtime, no_document)

        # Assert
        self.assertEqual(reports, [])
