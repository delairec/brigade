import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.report_list import COMMAND
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

    def test_should_print_a_dash_for_the_kind_of_the_result_of_an_order_no_longer_recorded(self):
        # Arrange
        document = {
            "schema_version": 1,
            "reports": [{"id": "gone_r1", "kind": None, "project": None}],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "id       kind  project\ngone_r1  -     -")

    def test_should_say_there_is_no_report(self):
        # Arrange
        document = {"schema_version": 1, "reports": []}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "no report")


MILESTONE_REPORT_WITH_NARRATIVE = {
    "type": "REPORT",
    "name": "brigade_M13",
    "fields": [
        {"name": "MILESTONE", "value": "M13"},
        {"name": "PROJECT", "value": "brigade"},
        {"name": "STATISTIC", "value": "tasks 4"},
        {"name": "STATISTIC", "value": "merged 3"},
        {"name": "NARRATIVE", "value": "Verdict: M13 delivered three of its four tasks."},
        {"name": "NARRATIVE", "value": "B91 parked on its review."},
    ],
}
WAVE_REPORT_WITHOUT_NARRATIVE = {
    "type": "REPORT",
    "name": "oak_w3",
    "fields": [
        {"name": "WAVE", "value": "oak_w3"},
        {"name": "PROJECT", "value": "oak"},
        {"name": "STATISTIC", "value": "tasks 1"},
        {"name": "STATISTIC", "value": "merged 0"},
    ],
}
MILESTONE_REPORT_WITH_GATE_ROWS = {
    "type": "REPORT",
    "name": "brigade_M14",
    "fields": [
        {"name": "MILESTONE", "value": "M14"},
        {"name": "PROJECT", "value": "brigade"},
        {"name": "STATISTIC", "value": "tasks 2"},
        {"name": "STATISTIC", "value": "rounds to pass B21 1"},
        {"name": "STATISTIC", "value": "rounds to pass B22 3"},
        {"name": "STATISTIC", "value": "escapes 1 of 2"},
    ],
}
TASK_REPORT = {
    "type": "REPORT",
    "name": "brigade_B231",
    "fields": [{"name": "TASK", "value": "B231"}, {"name": "PROJECT", "value": "brigade"}],
}
M13_REPORTED_FIRST = {
    "schema_version": 1,
    "ts": "2026-10-17T08:00:00Z",
    "event": "milestone.reported",
    "project": "brigade",
    "milestone": "M13",
    "run": "20261017T080000Z-aaaaaa",
    "login": None,
}
M13_REPORTED_AGAIN = {**M13_REPORTED_FIRST, "ts": "2026-10-18T10:00:00Z", "run": "20261018T100000Z-bbbbbb"}
M12_REPORTED = {**M13_REPORTED_FIRST, "ts": "2026-10-19T11:00:00Z", "milestone": "M12"}
M13_OF_ANOTHER_PROJECT_REPORTED = {**M13_REPORTED_FIRST, "ts": "2026-10-19T12:00:00Z", "project": "oak"}
B231_REPORTED = {
    "schema_version": 1,
    "ts": "2026-10-12T09:30:00Z",
    "event": "task.reported",
    "project": "brigade",
    "task": "B231",
    "run": "20261012T093000Z-cccccc",
    "login": None,
}
OAK_W3_REPORTED = {
    "schema_version": 1,
    "ts": "2026-10-05T07:15:00Z",
    "event": "wave.reported",
    "wave": "oak_w3",
    "run": None,
}
OAK_W3_CLOSED = {
    "schema_version": 1,
    "ts": "2026-10-05T07:20:00Z",
    "event": "wave.closed",
    "wave": "oak_w3",
    "pr": None,
}
NOTHING_REPORTED = []
NO_REPORT = []
NO_RESULT = []
ORDER_RESULT = {
    "type": "RESULT",
    "name": "nightly_20261019T090000Z_a1",
    "fields": [{"name": "ORDER", "value": "nightly"}, {"name": "NARRATIVE", "value": "The disk holds 12 GB of runs."}],
}


class ReportsListOfTheOperationalCorpusTest(unittest.TestCase):
    def list_reports(self, reports: list[dict], ledger: list[dict], results: list[dict] = NO_RESULT) -> list[dict]:
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(root)
        (root / "config" / "reports.awawa").write_text("", encoding="utf-8")
        (root / "config" / "results.awawa").write_text("", encoding="utf-8")
        write_ledger(root, ledger)
        plugin = DocumentPluginDouble(
            {str(root / "config" / "reports.awawa"): reports, str(root / "config" / "results.awawa"): results}
        )
        no_study = {}
        runtime = create_test_runtime(
            create_test_paths(root),
            run_process=create_corpus_double(no_study),
            resolve_plugin=create_plugin_resolver({("progress_form", "awawa"): plugin}),
        )
        return COMMAND.run(Namespace(), runtime)["reports"]

    def test_should_describe_a_report_by_its_identity_its_subject_its_figures_and_its_verdict(self):
        # Act
        reports = self.list_reports([MILESTONE_REPORT_WITH_NARRATIVE], [M13_REPORTED_FIRST])

        # Assert
        self.assertEqual(
            reports,
            [
                {
                    "id": "brigade_M13",
                    "kind": "milestone-report",
                    "project": "brigade",
                    "subject": "M13",
                    "statistics": {"tasks": "4", "merged": "3"},
                    "verdict": "Verdict: M13 delivered three of its four tasks.",
                    "counts": {"MILESTONE": 1, "PROJECT": 1, "STATISTIC": 2, "NARRATIVE": 2},
                    "reported_at": "2026-10-17T08:00:00Z",
                    "title": None,
                }
            ],
        )

    def test_should_name_the_milestone_the_task_or_the_wave_a_report_reports(self):
        # Act
        reports = self.list_reports([MILESTONE_REPORT_WITH_NARRATIVE, TASK_REPORT, WAVE_REPORT_WITHOUT_NARRATIVE], [])

        # Assert
        self.assertEqual(reports[0]["subject"], "M13")
        self.assertEqual(reports[1]["subject"], "B231")
        self.assertEqual(reports[2]["subject"], "oak_w3")

    def test_should_name_no_subject_for_the_result_of_an_order(self):
        # Act
        reports = self.list_reports(NO_REPORT, NOTHING_REPORTED, [ORDER_RESULT])

        # Assert
        self.assertIsNone(reports[0]["subject"])

    def test_should_carry_the_statistics_of_a_report_by_their_name(self):
        # Act
        reports = self.list_reports([WAVE_REPORT_WITHOUT_NARRATIVE], NOTHING_REPORTED)

        # Assert
        self.assertEqual(reports[0]["statistics"], {"tasks": "1", "merged": "0"})

    def test_should_carry_the_rounds_to_pass_of_each_task_and_the_escapes_of_a_milestone_report(self):
        # Act
        reports = self.list_reports([MILESTONE_REPORT_WITH_GATE_ROWS], NOTHING_REPORTED)

        # Assert
        self.assertEqual(
            reports[0]["statistics"],
            {"tasks": "2", "rounds to pass B21": "1", "rounds to pass B22": "3", "escapes": "1 of 2"},
        )

    def test_should_give_no_verdict_to_a_report_holding_no_narrative(self):
        # Act
        reports = self.list_reports([MILESTONE_REPORT_WITH_NARRATIVE, WAVE_REPORT_WITHOUT_NARRATIVE], NOTHING_REPORTED)

        # Assert
        self.assertEqual(reports[0]["verdict"], "Verdict: M13 delivered three of its four tasks.")
        self.assertIsNone(reports[1]["verdict"])

    def test_should_count_the_values_of_a_report_by_field_name(self):
        # Act
        reports = self.list_reports([WAVE_REPORT_WITHOUT_NARRATIVE], NOTHING_REPORTED)

        # Assert
        self.assertEqual(reports[0]["counts"], {"WAVE": 1, "PROJECT": 1, "STATISTIC": 2})

    def test_should_date_each_report_by_the_last_event_of_the_ledger_that_recorded_it(self):
        # Arrange
        ledger = [
            M13_REPORTED_FIRST,
            OAK_W3_REPORTED,
            B231_REPORTED,
            M13_REPORTED_AGAIN,
            M12_REPORTED,
            M13_OF_ANOTHER_PROJECT_REPORTED,
        ]

        # Act
        reports = self.list_reports(
            [MILESTONE_REPORT_WITH_NARRATIVE, TASK_REPORT, WAVE_REPORT_WITHOUT_NARRATIVE], ledger
        )

        # Assert
        self.assertEqual(reports[0]["reported_at"], "2026-10-18T10:00:00Z")
        self.assertEqual(reports[1]["reported_at"], "2026-10-12T09:30:00Z")
        self.assertEqual(reports[2]["reported_at"], "2026-10-05T07:15:00Z")

    def test_should_date_a_report_by_the_event_that_recorded_it_among_the_others_of_the_ledger(self):
        # Act
        reports = self.list_reports([WAVE_REPORT_WITHOUT_NARRATIVE], [OAK_W3_REPORTED, OAK_W3_CLOSED])

        # Assert
        self.assertEqual(reports[0]["reported_at"], "2026-10-05T07:15:00Z")

    def test_should_leave_undated_a_report_the_ledger_holds_no_event_for(self):
        # Act
        reports = self.list_reports([WAVE_REPORT_WITHOUT_NARRATIVE], [M13_REPORTED_FIRST])

        # Assert
        self.assertIsNone(reports[0]["reported_at"])


class ReportsListOfAMilestoneOfARegisteredProjectTest(unittest.TestCase):
    def test_should_title_the_report_by_the_milestone_of_the_corpus_of_its_project(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_operational_corpus(root)
        (root / "config" / "reports.awawa").write_text("", encoding="utf-8")
        write_ledger(root, NOTHING_REPORTED)
        plugin = DocumentPluginDouble({str(root / "config" / "reports.awawa"): [MILESTONE_REPORT_WITH_NARRATIVE]})
        registry = {"PROJECT": {"brigade": (("PATH", "/projects/brigade"), ("MODE", "control"))}}
        project_corpus = {"MILESTONE": {"M13": (("TITLE", "Run resumption"),)}}
        runtime = create_test_runtime(
            create_test_paths(root),
            run_process=create_corpora_double({str(root / "config"): registry, "/projects/brigade": project_corpus}),
            resolve_plugin=create_plugin_resolver({("progress_form", "awawa"): plugin}),
        )

        # Act
        reports = COMMAND.run(Namespace(), runtime)["reports"]

        # Assert
        self.assertEqual(reports[0]["title"], "Run resumption")
