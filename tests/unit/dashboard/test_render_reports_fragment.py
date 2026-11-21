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
    "title": None,
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
    "title": None,
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
    "title": None,
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
    "title": None,
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
    "title": None,
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
    "title": None,
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


def _bar(label: str, state: str, width: str) -> str:
    return (
        f'<svg class="bar" viewBox="0 0 100 8" role="img" aria-label="{label}">'
        '<rect class="bar-track" width="100" height="8"></rect>'
        f'<rect class="bar-fill tone-{state}" width="{width}" height="8"></rect></svg>'
    )


M8_REPORT = {
    "id": "brigade_M8",
    "kind": "milestone-report",
    "project": "brigade",
    "subject": "M8",
    "statistics": {"tasks": "12", "merged": "12", "runs": "88"},
    "verdict": "M8 is delivered, all 12 tasks merged.",
    "counts": {"MILESTONE": 1, "REASON": 6, "TESTER_STEP": 24, "NARRATIVE": 9},
    "reported_at": "2026-11-17T10:00:00Z",
    "title": None,
}
M13_FULL_REPORT = {
    "id": "brigade_M13",
    "kind": "milestone-report",
    "project": "brigade",
    "subject": "M13",
    "statistics": {"tasks": "4", "merged": "3", "runs": "22"},
    "verdict": "Verdict: M13 delivered three of its four tasks.",
    "counts": {"MILESTONE": 1, "REASON": 1, "TESTER_STEP": 1, "NARRATIVE": 3},
    "reported_at": "2026-11-18T10:00:00Z",
    "title": None,
}
W3_EMPTY = {
    "id": "oak_w3",
    "kind": "wave-report",
    "project": "oak",
    "subject": "oak_w3",
    "statistics": {"tasks": "1", "merged": "0", "runs": "2"},
    "verdict": "oak_w3 delivered nothing.",
    "counts": {"WAVE": 1},
    "reported_at": "2026-10-01T10:00:00Z",
    "title": None,
}
W4_DELIVERED = {
    "id": "oak_w4",
    "kind": "wave-report",
    "project": "oak",
    "subject": "oak_w4",
    "statistics": {"tasks": "2", "merged": "2"},
    "verdict": "oak_w4 delivered its two tasks.",
    "counts": {"WAVE": 1},
    "reported_at": "2026-10-02T10:00:00Z",
    "title": None,
}


class RenderReportsFragmentAsTheMockupTest(unittest.TestCase):
    def test_should_open_on_what_a_report_is_and_when_to_read_one_unfolded(self):
        # Act
        fragment = render_reports_fragment({"reports": [M8_REPORT]})

        # Assert
        self.assertIn(
            '</header><details class="explainer" open><summary>What a report is, and when to read one</summary>'
            "<div><p>When every task of a milestone is merged or parked, brigade writes its report. The <b>CLI fills"
            " the facts</b>: the tasks and their pull requests, the statistics, the SPEC lines to test. A <b>reporting"
            " agent writes the judgment</b>: the verdict, why a task was parked, what went well and wrong, the steps a"
            " tester follows, the code worth reading by sampling.</p>"
            "<p>The report is committed on the branch of the milestone and becomes the body of the pull request you"
            " merge. <b>Read it before that merge</b>, and after any wave you did not watch. If you read three things:"
            " the verdict, what went wrong, the tester steps.</p>"
            "<p>A task that names no milestone gets a task report. Reports named after a wave were written before"
            " milestone reports existed.</p></div></details>",
            fragment,
        )

    def test_should_list_the_milestones_newest_first_with_their_verdict_their_tasks_their_runs_and_what_they_hold(self):
        # Act
        fragment = render_reports_fragment({"reports": [M8_REPORT, M13_FULL_REPORT]})

        # Assert
        self.assertIn(
            '<section class="block"><div class="block-head"><h2>Milestones</h2><p>The newest first.</p></div>'
            '<div class="panel scroll"><table><thead><tr><th>Milestone</th><th>Verdict</th><th>Tasks</th>'
            '<th class="num">Runs</th><th>Inside</th></tr></thead><tbody>'
            '<tr><td><a href="#reports/brigade_M13"><b class="mono">M13</b></a></td>'
            "<td>M13 delivered three of its four tasks.</td>"
            f'<td>{_bar("3 of 4 merged", "you", "75")}<span class="muted num">3 of 4 merged</span></td>'
            '<td class="num">22</td><td class="num">1 reason · 1 tester step</td></tr>'
            '<tr><td><a href="#reports/brigade_M8"><b class="mono">M8</b></a></td>'
            "<td>M8 is delivered, all 12 tasks merged.</td>"
            f'<td>{_bar("12 of 12 merged", "done", "100")}<span class="muted num">12 of 12 merged</span></td>'
            '<td class="num">88</td><td class="num">6 reasons · 24 tester steps</td></tr>'
            "</tbody></table></div></section>",
            fragment,
        )

    def test_should_give_a_milestone_its_title_under_its_name(self):
        # Act
        fragment = render_reports_fragment({"reports": [{**M13_FULL_REPORT, "title": "Run resumption"}]})

        # Assert
        self.assertIn(
            '<tr><td><a href="#reports/brigade_M13"><b class="mono">M13</b></a>'
            '<br><span class="muted">Run resumption</span></td>',
            fragment,
        )

    def test_should_fold_the_wave_reports_under_how_many_delivered_and_which_delivered_nothing(self):
        # Act
        fragment = render_reports_fragment({"reports": [W3_EMPTY, W4_DELIVERED]})

        # Assert
        self.assertIn(
            '<section class="block"><div class="block-head"><h2>Waves, before milestone reports</h2>'
            '<p>2 reports.</p></div><div class="panel"><details class="fold"><summary>Show the wave reports'
            " <span>· 1 delivered at least one task · 1 delivered nothing: oak_w3</span></summary>"
            '<div class="scroll"><table><thead><tr><th>Wave</th><th>Verdict</th><th>Tasks</th>'
            '<th class="num">Runs</th></tr></thead><tbody>'
            '<tr><td><a class="mono" href="#reports/oak_w4">oak_w4</a></td><td>oak_w4 delivered its two tasks.</td>'
            f'<td>{_bar("2 of 2 merged", "done", "100")}<span class="muted num">2 of 2 merged</span></td>'
            '<td class="num">-</td></tr>',
            fragment,
        )

    def test_should_escape_a_subject_and_a_verdict_holding_markup(self):
        # Arrange
        report = {**M8_REPORT, "subject": "<b>M13</b>", "verdict": "<script>x</script>"}

        # Act
        fragment = render_reports_fragment({"reports": [report, {**W3_EMPTY, "verdict": None}]})

        # Assert
        self.assertNotIn("<script>", fragment)
        self.assertIn("&lt;b&gt;M13&lt;/b&gt;", fragment)

    def test_should_say_no_wave_delivered_nothing(self):
        # Act
        fragment = render_reports_fragment({"reports": [W4_DELIVERED]})

        # Assert
        self.assertIn("<span>· 1 delivered at least one task</span>", fragment)
