import unittest

from brigade.dashboard.render_report_fragment import ReportReading, render_report_fragment

NO_FORGE = None
NO_WAVE = []


def create_document(fields: list[dict]) -> dict:
    return {
        "schema_version": 1,
        "report": {
            "id": "oak_M4",
            "kind": "milestone-report",
            "project": "oak",
            "pattern": None,
            "type": "REPORT",
            "fields": fields,
        },
        "waves": ["oak_w5"],
        "pull_request": 57,
        "reported_at": "2026-10-03T08:00:00Z",
    }


def create_wave(unmeasured_runs: int = 0, states: tuple[str, str] = ("merged", "merged")) -> dict:
    return {
        "wave": "oak_w5",
        "tasks": [
            {"task": "OK7", "state": states[0], "pull_request": 52, "run": "20261001T090000Z-a1", "reason": None},
            {"task": "OK8", "state": states[1], "pull_request": 53, "run": "20261001T100000Z-b2", "reason": None},
        ],
        "ledger": {
            "wall_time_ms": 17400000,
            "cost_usd": 41.28,
            "by_task": [
                {"task": "OK7", "turns": 104, "partial": False, "duration_ms": 2100000, "cost_usd": 6.85},
                {"task": "OK8", "turns": 23, "partial": False, "duration_ms": 900000, "cost_usd": 1.15},
            ],
            "turns": {
                "by_slot": {
                    "build": {"runs": {"measured": 4, "unmeasured": unmeasured_runs, "p50": 73, "p90": 253}},
                    "review": {"runs": {"measured": 3, "unmeasured": 0, "p50": 16, "p90": 40}},
                }
            },
            "turns_by_task": {"OK7": 104, "OK8": 23},
        },
    }


def render(fields: list[dict], waves: list[dict] = NO_WAVE, address: str | None = NO_FORGE) -> str:
    return render_report_fragment(ReportReading(create_document(fields), waves, address))


class RenderReportFragmentOrderTest(unittest.TestCase):
    def test_should_open_on_the_verdict_and_order_the_blocks_by_use_whatever_the_order_written(self):
        # Arrange
        fields = [
            {"name": "MILESTONE", "value": "M4"},
            {"name": "SAMPLING", "value": "OK7, oak/bark.py: the guard"},
            {"name": "NARRATIVE", "value": "next: split OK9 first"},
            {"name": "REASON", "value": "OK9 waits for a ruling"},
            {"name": "NARRATIVE", "value": "Went well: one round of review"},
            {"name": "TESTER_STEP", "value": "OK7: run oak bark"},
            {"name": "NARRATIVE", "value": "M4 delivered two tasks"},
            {"name": "TASK_ROW", "value": "OK7 merged #52"},
            {"name": "NARRATIVE", "value": "went wrong: a rebase conflicted"},
            {"name": "NARRATIVE", "value": "VERDICT: delivered"},
        ]

        # Act
        fragment = render(fields, [create_wave()])

        # Assert
        self.assertRegex(
            fragment,
            r"(?s)^<section class=\"report-verdict\"><h2>milestone-report oak_M4</h2>"
            r"<p class=\"status-sentence\">VERDICT: delivered</p>.*"
            r"<div class=\"tiles\">.*<h3>Went wrong</h3><ul><li>went wrong: a rebase conflicted</li></ul>"
            r"<h3>Went well</h3><ul><li>Went well: one round of review</li></ul>"
            r"<h3>For the next wave</h3><ul><li>next: split OK9 first</li></ul>"
            r"<ul><li>M4 delivered two tasks</li></ul>"
            r"<h3>Tasks</h3>.*<h3>Test it by hand</h3>.*<h3>Why a task was held</h3>.*"
            r"<h3>Worth reading in the code</h3>.*"
            r"<details><summary>The full account</summary><dl><dt>MILESTONE</dt><dd>M4</dd></dl></details>$",
        )


class RenderReportFragmentOfANarrativeOpeningOnNoLeadingWordTest(unittest.TestCase):
    def test_should_show_the_narrative_as_one_list_in_the_order_written(self):
        # Arrange
        fields = [
            {"name": "NARRATIVE", "value": "M8 delivered three tasks"},
            {"name": "NARRATIVE", "value": "two waves were needed"},
        ]

        # Act
        fragment = render(fields)

        # Assert
        self.assertEqual(
            fragment,
            '<section class="report-verdict"><h2>milestone-report oak_M4</h2>'
            '<p class="report-delivery">reported 2026-10-03T08:00:00Z, pull request #57</p></section>'
            "<ul><li>M8 delivered three tasks</li><li>two waves were needed</li></ul>",
        )


class RenderReportFragmentDeliveryTest(unittest.TestCase):
    def test_should_give_the_instant_alone_when_no_pull_request_is_recorded(self):
        # Arrange
        document = {**create_document([]), "pull_request": None}

        # Act
        fragment = render_report_fragment(ReportReading(document, NO_WAVE, NO_FORGE))

        # Assert
        self.assertEqual(
            fragment,
            '<section class="report-verdict"><h2>milestone-report oak_M4</h2>'
            '<p class="report-delivery">reported 2026-10-03T08:00:00Z</p></section>',
        )

    def test_should_give_no_delivery_line_when_the_ledger_records_neither_the_instant_nor_the_pull_request(self):
        # Arrange
        document = {**create_document([]), "pull_request": None, "reported_at": None}

        # Act
        fragment = render_report_fragment(ReportReading(document, NO_WAVE, NO_FORGE))

        # Assert
        self.assertEqual(fragment, '<section class="report-verdict"><h2>milestone-report oak_M4</h2></section>')


class RenderReportFragmentGroupingTest(unittest.TestCase):
    def test_should_list_a_step_naming_no_task_under_no_task_heading(self):
        # Arrange
        fields = [
            {"name": "TESTER_STEP", "value": "open the dashboard"},
            {"name": "TESTER_STEP", "value": "OK7: run oak bark"},
        ]

        # Act
        fragment = render(fields)

        # Assert
        self.assertIn(
            "<h3>Test it by hand</h3><ol><li>open the dashboard</li></ol><h4>OK7</h4><ol><li>OK7: run oak bark</li></ol>",
            fragment,
        )

    def test_should_group_the_steps_to_test_by_hand_and_the_samples_by_the_task_they_name(self):
        # Arrange
        fields = [
            {"name": "TESTER_STEP", "value": "OK8: open the page"},
            {"name": "MANUAL_TEST", "value": "OK7: the bark is listed"},
            {"name": "TESTER_STEP", "value": "OK7: run oak bark"},
            {"name": "TESTER_STEP", "value": "OK8: close the page"},
            {"name": "SAMPLING", "value": "OK8, oak/page.py: the swap"},
        ]

        # Act
        fragment = render(fields)

        # Assert
        self.assertIn(
            "<h3>Test it by hand</h3>"
            "<h4>OK8</h4><ol><li>OK8: open the page</li><li>OK8: close the page</li></ol>"
            "<h4>OK7</h4><ol><li>OK7: run oak bark</li></ol><ul><li>OK7: the bark is listed</li></ul>"
            "<h3>Worth reading in the code</h3><h4>OK8</h4><ul><li>OK8, oak/page.py: the swap</li></ul>",
            fragment,
        )


class RenderReportFragmentTablesTest(unittest.TestCase):
    def test_should_draw_the_task_rows_and_the_graph_as_tables(self):
        # Arrange
        fields = [
            {"name": "TASK_ROW", "value": "OK7 merged #52"},
            {"name": "TASK_ROW", "value": "OK8 parked"},
            {"name": "GRAPH", "value": "OK8 after OK7"},
        ]

        # Act
        fragment = render(fields)

        # Assert
        self.assertIn(
            "<h3>Tasks</h3>"
            "<table><thead><tr><th>task</th></tr></thead>"
            "<tbody><tr><td>OK7 merged #52</td></tr><tr><td>OK8 parked</td></tr></tbody></table>"
            "<table><thead><tr><th>dependency</th></tr></thead>"
            "<tbody><tr><td>OK8 after OK7</td></tr></tbody></table>",
            fragment,
        )


class RenderReportFragmentLinksTest(unittest.TestCase):
    def test_should_link_the_wave_of_a_task_the_pull_request_on_the_forge_and_the_page_of_a_run(self):
        # Arrange
        fields = [{"name": "REASON", "value": "OK8 #53 stopped in 20261001T100000Z-b2, M4 is open"}]

        # Act
        fragment = render(fields, [create_wave()], "https://forge.example/oak/pull/")

        # Assert
        self.assertIn(
            '<li><a href="#waves/oak_w5">OK8</a> <a href="https://forge.example/oak/pull/53">#53</a> stopped in '
            '<a href="#runs/20261001T100000Z-b2">20261001T100000Z-b2</a>, M4 is open</li>',
            fragment,
        )

    def test_should_leave_a_pull_request_unlinked_when_the_project_names_no_forge(self):
        # Arrange
        fields = [{"name": "REASON", "value": "#53 was closed"}]

        # Act
        fragment = render(fields, [create_wave()])

        # Assert
        self.assertIn("<li>#53 was closed</li>", fragment)


class RenderReportFragmentTilesTest(unittest.TestCase):
    def test_should_give_the_measures_of_the_waves_named(self):
        # Arrange
        fields = [{"name": "STATISTIC", "value": "files 12"}]

        # Act
        fragment = render(fields, [create_wave()])

        # Assert
        self.assertIn(
            '<div class="tiles">'
            '<div class="stat-tile"><span class="stat-value">2 of 2</span><span class="stat-label">tasks merged</span>'
            '<span class="stat-perimeter">the waves oak_w5</span></div>'
            '<div class="stat-tile"><span class="stat-value">7 runs, 127 turns</span><span class="stat-label">runs</span>'
            '<span class="stat-perimeter">the waves oak_w5</span></div>'
            '<div class="stat-tile"><span class="stat-value">41.28 USD</span><span class="stat-label">cost</span>'
            '<span class="stat-perimeter">the waves oak_w5</span></div>'
            '<div class="stat-tile"><span class="stat-value">4 h 50 min</span><span class="stat-label">wall time</span>'
            '<span class="stat-perimeter">50 min of run time</span></div>'
            '<div class="stat-tile"><span class="stat-value">12</span><span class="stat-label">files changed</span>'
            '<span class="stat-perimeter">the statistic of the report</span></div>'
            "</div>",
            fragment,
        )

    def test_should_mark_the_cost_a_floor_when_a_run_records_none(self):
        # Arrange
        fields = [{"name": "STATISTIC", "value": "files 12"}]

        # Act
        fragment = render(fields, [create_wave(unmeasured_runs=2)])

        # Assert
        self.assertIn(
            '<span class="stat-value">41.28 USD</span><span class="stat-label">cost</span>'
            '<span class="stat-perimeter">a floor: 2 runs record no cost</span>',
            fragment,
        )

    def test_should_question_no_file_changed_when_the_ledger_records_tasks_merged(self):
        # Arrange
        fields = [{"name": "STATISTIC", "value": "files 0"}]

        # Act
        fragment = render(fields, [create_wave()])

        # Assert
        self.assertIn(
            '<div class="stat-tile questioned"><span class="stat-value">0</span>'
            '<span class="stat-label">files changed</span>'
            '<span class="stat-perimeter">questioned: the ledger records 2 tasks merged</span></div>',
            fragment,
        )

    def test_should_leave_no_file_changed_unquestioned_when_no_task_merged(self):
        # Arrange
        fields = [{"name": "STATISTIC", "value": "files 0"}]

        # Act
        fragment = render(fields, [create_wave(states=("parked", "parked"))])

        # Assert
        self.assertIn(
            '<div class="stat-tile"><span class="stat-value">0</span><span class="stat-label">files changed</span>',
            fragment,
        )


class RenderReportFragmentEscapingTest(unittest.TestCase):
    def test_should_escape_a_value_holding_markup(self):
        # Arrange
        fields = [
            {"name": "NARRATIVE", "value": "Verdict: <script>alert(1)</script>"},
            {"name": "<i>WAVE</i>", "value": "<b>oak_w3</b>"},
        ]

        # Act
        fragment = render(fields)

        # Assert
        self.assertEqual(
            fragment,
            '<section class="report-verdict"><h2>milestone-report oak_M4</h2>'
            '<p class="status-sentence">Verdict: &lt;script&gt;alert(1)&lt;/script&gt;</p>'
            '<p class="report-delivery">reported 2026-10-03T08:00:00Z, pull request #57</p></section>'
            "<details><summary>The full account</summary>"
            "<dl><dt>&lt;i&gt;WAVE&lt;/i&gt;</dt><dd>&lt;b&gt;oak_w3&lt;/b&gt;</dd></dl></details>",
        )
