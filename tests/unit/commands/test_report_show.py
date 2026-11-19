import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.report_show import COMMAND
from brigade.errors import BrigadeError
from tests.unit.commands.command_runtime import create_corpus_double, write_ledger, write_operational_corpus
from tests.unit.commands.create_plugin_resolver import create_plugin_resolver
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.reports.document_plugin_double import DocumentPluginDouble

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
            },
        )


def write_delivery(root: Path) -> None:
    write_ledger(
        root,
        [
            {
                "schema_version": 1,
                "ts": "2026-10-01T08:00:00Z",
                "event": "milestone.branch_cut",
                "project": "oak",
                "milestone": "M4",
                "branch": "integration/roots",
                "login": None,
            },
            {
                "schema_version": 2,
                "ts": "2026-10-01T09:00:00Z",
                "event": "wave.started",
                "wave": "oak_w5",
                "project": "oak",
                "tasks": ["OK7"],
                "branch": "integration/roots",
            },
            {
                "schema_version": 2,
                "ts": "2026-10-01T09:30:00Z",
                "event": "wave.started",
                "wave": "elm_w5",
                "project": "elm",
                "tasks": ["OK7"],
                "branch": "integration/roots",
            },
            {
                "schema_version": 2,
                "ts": "2026-10-02T09:00:00Z",
                "event": "wave.started",
                "wave": "oak_w6",
                "project": "oak",
                "tasks": ["OK8"],
                "branch": "integration/roots",
            },
            {
                "schema_version": 2,
                "ts": "2026-10-02T10:00:00Z",
                "event": "wave.started",
                "wave": "oak_w7",
                "project": "oak",
                "tasks": ["OK9"],
            },
            {
                "schema_version": 1,
                "ts": "2026-10-02T11:00:00Z",
                "event": "task.pr_opened",
                "project": "oak",
                "task": "OK9",
                "wave": "oak_w7",
                "branch": "feature/OK9-bark",
                "pr": 52,
                "login": "bot",
            },
            {
                "schema_version": 1,
                "ts": "2026-10-02T12:00:00Z",
                "event": "task.reported",
                "project": "oak",
                "task": "OK9",
                "run": "20261002T120000Z-c3",
                "login": None,
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
            {
                "schema_version": 1,
                "ts": "2026-10-04T09:00:00Z",
                "event": "wave.reported",
                "wave": "oak_w3",
                "run": None,
            },
            {
                "schema_version": 1,
                "ts": "2026-10-04T10:00:00Z",
                "event": "wave.pr_opened",
                "wave": "oak_w3",
                "pr": 31,
                "login": None,
            },
        ],
    )


def show_delivery(root: Path, report: dict) -> dict:
    document = COMMAND.run(Namespace(id=report["name"]), create_runtime(root, report))
    return {key: document[key] for key in ("waves", "pull_request", "reported_at")}


class ReportsShowOfAMilestoneReportTest(unittest.TestCase):
    def test_should_name_the_waves_of_its_milestone_its_pull_request_and_the_instant_it_was_reported(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_delivery(root)
        report = {
            "type": "REPORT",
            "name": "oak_M4",
            "fields": [{"name": "MILESTONE", "value": "M4"}, {"name": "PROJECT", "value": "oak"}],
        }

        # Act
        delivery = show_delivery(root, report)

        # Assert
        self.assertEqual(
            delivery, {"waves": ["oak_w5", "oak_w6"], "pull_request": 57, "reported_at": "2026-10-03T08:00:00Z"}
        )


class ReportsShowOfATaskReportTest(unittest.TestCase):
    def test_should_name_the_wave_of_its_task_its_pull_request_and_the_instant_it_was_reported(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_delivery(root)
        report = {
            "type": "REPORT",
            "name": "oak_OK9",
            "fields": [{"name": "TASK", "value": "OK9"}, {"name": "PROJECT", "value": "oak"}],
        }

        # Act
        delivery = show_delivery(root, report)

        # Assert
        self.assertEqual(delivery, {"waves": ["oak_w7"], "pull_request": 52, "reported_at": "2026-10-02T12:00:00Z"})


class ReportsShowOfAWaveReportTest(unittest.TestCase):
    def test_should_name_its_wave_its_pull_request_and_the_instant_it_was_reported(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_delivery(root)
        report = {
            "type": "REPORT",
            "name": "oak_w3",
            "fields": [{"name": "WAVE", "value": "oak_w3"}, {"name": "PROJECT", "value": "oak"}],
        }

        # Act
        delivery = show_delivery(root, report)

        # Assert
        self.assertEqual(delivery, {"waves": ["oak_w3"], "pull_request": 31, "reported_at": "2026-10-04T09:00:00Z"})


class ReportsShowOfAMilestoneReportTheLedgerDoesNotRecordTest(unittest.TestCase):
    def test_should_name_no_wave_no_pull_request_and_no_instant(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        report = {
            "type": "REPORT",
            "name": "oak_M9",
            "fields": [{"name": "MILESTONE", "value": "M9"}, {"name": "PROJECT", "value": "oak"}],
        }

        # Act
        delivery = show_delivery(root, report)

        # Assert
        self.assertEqual(delivery, {"waves": [], "pull_request": None, "reported_at": None})


class ReportsShowOfAnUnknownReportTest(unittest.TestCase):
    def test_should_refuse_naming_the_id(self):
        # Arrange
        runtime = create_runtime(Path(self.enterContext(tempfile.TemporaryDirectory())))

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(Namespace(id="oak_w9"), runtime)

        # Assert
        self.assertEqual(str(raised.exception), "no report oak_w9")
