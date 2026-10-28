import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.reports_list import COMMAND
from tests.unit.commands.command_runtime import create_corpus_double, write_operational_corpus
from tests.unit.commands.create_plugin_resolver import create_plugin_resolver
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.reports.document_plugin_double import DocumentPluginDouble


class ReportsListTextTest(unittest.TestCase):
    def test_should_print_one_row_per_report(self):
        # Arrange
        document = {
            "schema_version": 1,
            "reports": [
                {"id": "oak_w3", "kind": "wave-report", "project": "oak"},
                {"id": "disk_r2", "kind": "study-answer", "project": None},
            ],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "id       kind          project\noak_w3   wave-report   oak\ndisk_r2  study-answer  -")

    def test_should_say_there_is_no_report(self):
        # Arrange
        document = {"schema_version": 1, "reports": []}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "no report")


class ReportsListOfTheOperationalCorpusTest(unittest.TestCase):
    def test_should_list_each_report_with_its_id_its_kind_and_its_project(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(root)
        (root / "config" / "reports.awawa").write_text("", encoding="utf-8")
        report = {"type": "REPORT", "name": "oak_w3", "fields": [{"name": "PROJECT", "value": "oak"}]}
        plugin = DocumentPluginDouble({str(root / "config" / "reports.awawa"): [report]})
        no_study = {}
        runtime = create_test_runtime(
            create_test_paths(root),
            run_process=create_corpus_double(no_study),
            resolve_plugin=create_plugin_resolver({("document", "awawa"): plugin}),
        )

        # Act
        document = COMMAND.run(Namespace(), runtime)

        # Assert
        self.assertEqual(
            document, {"schema_version": 1, "reports": [{"id": "oak_w3", "kind": "wave-report", "project": "oak"}]}
        )
