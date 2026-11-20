import unittest

from brigade.dashboard.render_reports_fragment import render_reports_fragment

M13_REPORT = {
    "id": "brigade_M13",
    "kind": "milestone-report",
    "project": "brigade",
    "subject": "M13",
    "statistics": {"tasks": "4", "merged": "3"},
    "verdict": "Verdict: M13 delivered three of its four tasks.",
    "counts": {"MILESTONE": 1, "PROJECT": 1, "STATISTIC": 2, "NARRATIVE": 1},
    "reported_at": "2026-11-18T10:00:00Z",
}
B231_REPORT = {
    "id": "brigade_B231",
    "kind": "task-report",
    "project": "brigade",
    "subject": "B231",
    "statistics": {"tasks": "1", "merged": "1"},
    "verdict": "B231 merged at its first review.",
    "counts": {"TASK": 1, "PROJECT": 1, "STATISTIC": 2, "NARRATIVE": 1},
    "reported_at": "2026-11-12T09:30:00Z",
}
OAK_W3_REPORT_WITHOUT_VERDICT = {
    "id": "oak_w3",
    "kind": "wave-report",
    "project": "oak",
    "subject": "oak_w3",
    "statistics": {"tasks": "1", "merged": "0"},
    "verdict": None,
    "counts": {"WAVE": 1, "PROJECT": 1, "STATISTIC": 2},
    "reported_at": None,
}
OAK_W4_REPORT = {
    "id": "oak_w4",
    "kind": "wave-report",
    "project": "oak",
    "subject": "oak_w4",
    "statistics": {"tasks": "2", "merged": "2"},
    "verdict": "The wave merged both its tasks.",
    "counts": {"WAVE": 1, "PROJECT": 1, "STATISTIC": 2, "NARRATIVE": 1},
    "reported_at": "2026-10-05T07:15:00Z",
}
OAK_W5_REPORT_MERGING_NOTHING = {
    "id": "oak_w5",
    "kind": "wave-report",
    "project": "oak",
    "subject": "oak_w5",
    "statistics": {"tasks": "3", "merged": "0"},
    "verdict": "The wave parked its three tasks.",
    "counts": {"WAVE": 1, "PROJECT": 1, "STATISTIC": 2, "NARRATIVE": 1},
    "reported_at": "2026-10-12T08:00:00Z",
}
DISK_ORDER_RESULT = {
    "id": "disk_r2",
    "kind": "disk-usage",
    "project": None,
    "subject": None,
    "statistics": {},
    "verdict": "The disk holds 12 GB of runs.",
    "counts": {"ORDER": 1, "RUN": 1, "NARRATIVE": 1},
    "reported_at": None,
}
NO_REPORT = []


class RenderReportsFragmentTest(unittest.TestCase):
    def test_should_open_on_one_sentence_counting_the_reports_by_kind(self):
        # Arrange
        reports = [M13_REPORT, B231_REPORT, OAK_W3_REPORT_WITHOUT_VERDICT, OAK_W4_REPORT, DISK_ORDER_RESULT]

        # Act
        fragment = render_reports_fragment({"schema_version": 1, "reports": reports})

        # Assert
        self.assertIn(
            '<div class="verdict"><p class="status-sentence">5 reports: 1 on a milestone, 1 on a task of no milestone,'
            " 2 on a wave, 1 answering an order.</p></div>",
            fragment,
        )

    def test_should_count_the_reports_of_each_kind_in_a_tile_and_the_waves_that_merged_nothing(self):
        # Arrange
        reports = [M13_REPORT, B231_REPORT, OAK_W3_REPORT_WITHOUT_VERDICT, OAK_W4_REPORT, OAK_W5_REPORT_MERGING_NOTHING]

        # Act
        fragment = render_reports_fragment({"schema_version": 1, "reports": reports})

        # Assert
        self.assertIn(
            '<div class="stat-tiles">'
            '<div class="stat-tile"><span class="stat-value">1</span>'
            '<span class="stat-label">milestone reports</span>'
            '<span class="stat-perimeter">one per milestone reached</span></div>'
            '<div class="stat-tile"><span class="stat-value">1</span>'
            '<span class="stat-label">task reports</span>'
            '<span class="stat-perimeter">one per task of no milestone</span></div>'
            '<div class="stat-tile"><span class="stat-value">3</span>'
            '<span class="stat-label">wave reports</span>'
            '<span class="stat-perimeter">2 record a wave that merged nothing</span></div>'
            "</div>",
            fragment,
        )

    def test_should_say_what_a_report_is_in_an_explainer_closed_on_its_summary_line(self):
        # Act
        fragment = render_reports_fragment({"schema_version": 1, "reports": NO_REPORT})

        # Assert
        self.assertIn(
            "<details><summary>A report is the account brigade writes once a delivery ends: a milestone"
            " reached, a task of no milestone ready to merge, or, before the milestone reports, a wave"
            ' closed.</summary><aside class="explainer"><p class="explainer-what">It tells what was'
            " delivered and what was not: the tasks merged and parked with their pull requests, the"
            " runs, the lines changed, the manual tests to run, the questions left, and a verdict"
            ' written on the evidence of the ledger.</p><p class="explainer-use">Read one before'
            " merging the pull request of a milestone or of a task, whose body it is, or to learn why"
            " a delivery went wrong: the verdict of each row says whether it is worth opening.</p>"
            "</aside></details>",
            fragment,
        )

    def test_should_list_the_reports_in_a_block_of_milestones_a_block_of_tasks_and_a_folded_block_of_waves(self):
        # Arrange
        reports = [OAK_W4_REPORT, M13_REPORT, B231_REPORT]

        # Act
        fragment = render_reports_fragment({"schema_version": 1, "reports": reports})

        # Assert
        self.assertIn(
            "<section><h2>Milestone reports</h2><table><thead><tr><th>subject</th><th>project</th>"
            "<th>verdict</th><th>tasks merged</th><th>reported</th></tr></thead><tbody>"
            '<tr><td><a href="#reports/brigade_M13">M13</a></td><td>brigade</td>'
            "<td>Verdict: M13 delivered three of its four tasks.</td><td>3 of 4</td>"
            '<td><time datetime="2026-11-18T10:00:00Z">2026-11-18</time></td></tr>'
            "</tbody></table></section>"
            "<section><h2>Task reports</h2><table><thead><tr><th>subject</th><th>project</th>"
            "<th>verdict</th><th>tasks merged</th><th>reported</th></tr></thead><tbody>"
            '<tr><td><a href="#reports/brigade_B231">B231</a></td><td>brigade</td>'
            "<td>B231 merged at its first review.</td><td>1 of 1</td>"
            '<td><time datetime="2026-11-12T09:30:00Z">2026-11-12</time></td></tr>'
            "</tbody></table></section>"
            "<section><h2>Wave reports</h2><details><summary>the reports of the waves, written before"
            " the milestone reports</summary><table><thead><tr><th>subject</th><th>project</th>"
            "<th>verdict</th><th>tasks merged</th><th>reported</th></tr></thead><tbody>"
            '<tr><td><a href="#reports/oak_w4">oak_w4</a></td><td>oak</td>'
            "<td>The wave merged both its tasks.</td><td>2 of 2</td>"
            '<td><time datetime="2026-10-05T07:15:00Z">2026-10-05</time></td></tr>'
            "</tbody></table></details></section>",
            fragment,
        )

    def test_should_read_a_report_without_narrative_as_carrying_no_verdict_and_no_date(self):
        # Act
        fragment = render_reports_fragment({"schema_version": 1, "reports": [OAK_W3_REPORT_WITHOUT_VERDICT]})

        # Assert
        self.assertIn(
            '<tr><td><a href="#reports/oak_w3">oak_w3</a></td><td>oak</td>'
            '<td><span class="no-verdict">no verdict recorded</span></td><td>0 of 1</td>'
            '<td><span class="no-date">not dated by the ledger</span></td></tr>',
            fragment,
        )

    def test_should_say_why_a_block_is_empty_and_what_would_fill_it(self):
        # Act
        fragment = render_reports_fragment({"schema_version": 1, "reports": NO_REPORT})

        # Assert
        self.assertIn(
            "<section><h2>Task reports</h2>"
            '<div class="empty-state"><p class="empty-why">No task of no milestone has been reported.</p>'
            '<p class="empty-fill">The tick writes one once the pull request of a task naming no milestone'
            " is ready.</p></div></section>",
            fragment,
        )

    def test_should_list_the_results_of_the_orders_after_the_three_blocks(self):
        # Act
        fragment = render_reports_fragment({"schema_version": 1, "reports": [DISK_ORDER_RESULT]})

        # Assert
        self.assertEqual(
            fragment.rpartition("<section>")[2],
            "<h2>Order results</h2><table><thead><tr><th>subject</th><th>project</th>"
            "<th>verdict</th><th>tasks merged</th><th>reported</th></tr></thead><tbody>"
            '<tr><td><a href="#reports/disk_r2">disk_r2</a></td><td>-</td>'
            "<td>The disk holds 12 GB of runs.</td><td>-</td>"
            '<td><span class="no-date">not dated by the ledger</span></td></tr>'
            "</tbody></table></section>",
        )

    def test_should_hold_no_block_of_order_results_when_no_order_answered(self):
        # Act
        fragment = render_reports_fragment({"schema_version": 1, "reports": [M13_REPORT]})

        # Assert
        self.assertNotIn("Order results", fragment)

    def test_should_escape_a_subject_and_a_verdict_holding_markup(self):
        # Arrange
        report = {**M13_REPORT, "id": "<i>x</i>", "subject": "<b>M13</b>", "verdict": "<script>alert(1)</script>"}

        # Act
        fragment = render_reports_fragment({"schema_version": 1, "reports": [report]})

        # Assert
        self.assertIn(
            '<tr><td><a href="#reports/%3Ci%3Ex%3C%2Fi%3E">&lt;b&gt;M13&lt;/b&gt;</a></td><td>brigade</td>'
            "<td>&lt;script&gt;alert(1)&lt;/script&gt;</td>",
            fragment,
        )


class RenderReportsFragmentHeadTest(unittest.TestCase):
    def test_should_open_on_the_page_head_naming_the_view_and_what_it_is_for(self):
        # Act
        fragment = render_reports_fragment({"schema_version": 1, "reports": []})

        # Assert
        self.assertTrue(
            fragment.startswith(
                '<header class="page-head"><div><h1>Reports</h1>'
                '<p class="lede">A report is the written account of a delivery: what was merged, what it cost, what went wrong, and what to check by hand before you trust it.</p></div>'
                '<p class="fresh num" data-fresh>refreshes every 5 s</p></header>'
            ),
            fragment[:300],
        )
