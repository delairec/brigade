import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.report_show import COMMAND
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import (
    create_corpora_double,
    create_corpus_double,
    write_ledger,
    write_operational_corpus,
)
from tests.unit.commands.create_plugin_resolver import create_plugin_resolver
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.reports.document_plugin_double import DocumentPluginDouble

MILESTONE_FIELDS = [
    {"name": "MILESTONE", "value": "M4"},
    {"name": "PROJECT", "value": "oak"},
    {"name": "TASK_ROW", "value": "OK7 merged #50"},
]
WAVE_REPORT = {"type": "REPORT", "name": "oak_w3", "fields": [{"name": "PROJECT", "value": "oak"}]}


def create_runtime(root: Path, report: dict = WAVE_REPORT):
    write_operational_corpus(root)
    (root / "config" / "reports.awawa").write_text("", encoding="utf-8")
    plugin = DocumentPluginDouble({str(root / "config" / "reports.awawa"): [report]})
    no_study = {}
    return create_test_runtime(
        create_test_paths(root),
        run_process=create_corpus_double(no_study),
        resolve_plugin=create_plugin_resolver({("progress_form", "awawa"): plugin}),
    )


class ReportsShowTextTest(unittest.TestCase):
    def test_should_print_the_markdown_rendered_from_the_entity(self):
        # Arrange
        document = {
            "schema_version": 1,
            "report": {
                "id": "oak_w3",
                "kind": "wave-report",
                "project": "oak",
                "pattern": None,
                "type": "REPORT",
                "fields": [{"name": "PROJECT", "value": "oak"}, {"name": "MANUAL_TEST", "value": "OK1: the page"}],
            },
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "# REPORT oak_w3\n\n- PROJECT: oak\n\n## Manual tests\n\n| # | test |\n| --- | --- |\n| 1 | OK1: the page |\n",
        )

    def test_should_name_the_pattern_the_order_of_a_result_comes_from(self):
        # Arrange
        document = {
            "schema_version": 1,
            "report": {
                "id": "CartTimeouts_20261019T090000Z_a1",
                "kind": "flaky-tests",
                "project": "shop",
                "pattern": "CartTimeouts",
                "type": "RESULT",
                "fields": [{"name": "ORDER", "value": "CartTimeouts"}],
            },
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text, "# RESULT CartTimeouts_20261019T090000Z_a1\n\n- PATTERN: CartTimeouts\n- ORDER: CartTimeouts\n"
        )


class ReportsShowOfAKnownReportTest(unittest.TestCase):
    def test_should_give_the_report_with_its_fields(self):
        # Arrange
        runtime = create_runtime(Path(self.enterContext(tempfile.TemporaryDirectory())))

        # Act
        document = COMMAND.run(Namespace(id="oak_w3"), runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "report": {
                    "id": "oak_w3",
                    "kind": "wave-report",
                    "project": "oak",
                    "pattern": None,
                    "type": "REPORT",
                    "fields": [{"name": "PROJECT", "value": "oak"}],
                },
                "waves": [],
                "pull_request": None,
                "reported_at": None,
                "title": None,
            },
        )


class ReportsShowOfTheResultOfAnOrderFromAPatternTest(unittest.TestCase):
    def test_should_give_the_pattern_the_order_comes_from(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(root)
        (root / "config" / "results.awawa").write_text("", encoding="utf-8")
        result = {
            "type": "RESULT",
            "name": "CartTimeouts_20261019T090000Z_a1",
            "fields": [{"name": "ORDER", "value": "CartTimeouts"}],
        }
        plugin = DocumentPluginDouble({str(root / "config" / "results.awawa"): [result]})
        orders = {
            "ORDER": {
                "CartTimeouts": (
                    ("RECIPE", "flaky-tests"),
                    ("PROJECT", "@PROJECT.shop"),
                    ("STATUS", "active"),
                    ("FROM", "@PATTERN.CartTimeouts"),
                ),
            }
        }
        runtime = create_test_runtime(
            create_test_paths(root),
            run_process=create_corpus_double(orders),
            resolve_plugin=create_plugin_resolver({("progress_form", "awawa"): plugin}),
        )

        # Act
        document = COMMAND.run(Namespace(id="CartTimeouts_20261019T090000Z_a1"), runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "report": {
                    "id": "CartTimeouts_20261019T090000Z_a1",
                    "kind": "flaky-tests",
                    "project": "shop",
                    "pattern": "CartTimeouts",
                    "type": "RESULT",
                    "fields": [{"name": "ORDER", "value": "CartTimeouts"}],
                },
                "waves": [],
                "pull_request": None,
                "reported_at": None,
                "title": None,
            },
        )


class ReportsShowOfADeliveredMilestoneReportTest(unittest.TestCase):
    def test_should_name_the_waves_of_its_milestone_its_pull_request_and_the_instant_it_was_reported(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_ledger(
            root,
            [
                {
                    "schema_version": 2,
                    "ts": "2026-10-01T09:00:00Z",
                    "event": "wave.started",
                    "wave": "oak_w5",
                    "project": "oak",
                    "tasks": ["OK7"],
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-03T08:00:00Z",
                    "event": "milestone.reported",
                    "project": "oak",
                    "milestone": "M4",
                    "run": "20261003T080000Z-a1",
                    "login": None,
                },
                {
                    "schema_version": 1,
                    "ts": "2026-10-03T09:00:00Z",
                    "event": "milestone.pr_opened",
                    "project": "oak",
                    "milestone": "M4",
                    "pr": 57,
                    "login": None,
                },
            ],
        )
        report = {
            "type": "REPORT",
            "name": "oak_M4",
            "fields": MILESTONE_FIELDS,
        }

        # Act
        document = COMMAND.run(Namespace(id="oak_M4"), create_runtime(root, report))

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "report": {
                    "id": "oak_M4",
                    "kind": "milestone-report",
                    "project": "oak",
                    "pattern": None,
                    "type": "REPORT",
                    "fields": MILESTONE_FIELDS,
                },
                "waves": ["oak_w5"],
                "pull_request": 57,
                "reported_at": "2026-10-03T08:00:00Z",
                "title": None,
            },
        )


class ReportsShowOfAMilestoneOfARegisteredProjectTest(unittest.TestCase):
    def test_should_title_the_report_by_the_milestone_of_the_corpus_of_its_project(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(root)
        (root / "config" / "reports.awawa").write_text("", encoding="utf-8")
        report = {"type": "REPORT", "name": "oak_M4", "fields": MILESTONE_FIELDS}
        plugin = DocumentPluginDouble({str(root / "config" / "reports.awawa"): [report]})
        registry = {"PROJECT": {"oak": (("PATH", "/projects/oak"), ("MODE", "control"))}}
        project_corpus = {"MILESTONE": {"M4": (("TITLE", "Checkout"),)}}
        runtime = create_test_runtime(
            create_test_paths(root),
            run_process=create_corpora_double({str(root / "config"): registry, "/projects/oak": project_corpus}),
            resolve_plugin=create_plugin_resolver({("progress_form", "awawa"): plugin}),
        )

        # Act
        document = COMMAND.run(Namespace(id="oak_M4"), runtime)

        # Assert
        self.assertEqual(document["title"], "Checkout")


class ReportsShowOfAnUnknownReportTest(unittest.TestCase):
    def test_should_refuse_naming_the_id(self):
        # Arrange
        runtime = create_runtime(Path(self.enterContext(tempfile.TemporaryDirectory())))

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(Namespace(id="oak_w9"), runtime)

        # Assert
        self.assertEqual(str(raised.exception), "no report oak_w9")
