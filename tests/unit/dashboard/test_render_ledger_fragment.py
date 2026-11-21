import json
import unittest

from brigade.dashboard.render_ledger_fragment import render_ledger_fragment
from brigade.dashboard.run_routed_command import CommandAnswer

OVERVIEW = {
    "schema_version": 1,
    "view": "overview",
    "events": {"run.finished": 6, "tick.action_failed": 4, "wave.started": 2},
    "first": "2026-11-17T21:10:00Z",
    "last": "2026-11-18T09:00:00Z",
    "files": ["/state/ledger/2026-11.jsonl"],
    "runs": {"outcomes": {"done": 4, "failed": 1}, "error_classes": {}},
    "segments": {"outcomes": {"done": 5, "turn_limit": 1}, "error_classes": {}},
    "waves_started": {"2026-11": ["w1", "<b>w2</b>"]},
    "failed_actions": {
        "by_day": {"2026-11-17": 1, "2026-11-18": 3},
        "by_action": {
            "MergeWavePullRequest": {"count": 1, "error": "not mergeable"},
            "<i>LaunchTask</i>": {"count": 3, "error": "quota <reached>"},
        },
    },
    "since": None,
    "skipped": [
        {"file": "/state/ledger/2026-11.jsonl", "line": 4, "reason": "not JSON"},
        {"file": "/state/ledger/2026-11.jsonl", "line": 9, "reason": "not JSON"},
    ],
}
EMPTY_OVERVIEW = {
    "schema_version": 1,
    "view": "overview",
    "events": {},
    "first": None,
    "last": None,
    "files": [],
    "runs": {"outcomes": {}, "error_classes": {}},
    "segments": {"outcomes": {}, "error_classes": {}},
    "waves_started": {},
    "failed_actions": {"by_day": {}, "by_action": {}},
    "since": None,
    "skipped": [],
}
BUDGETS = {
    "schema_version": 1,
    "last": 20,
    "procedures": {
        "build-task": {
            "runs": {"measured": 3, "unmeasured": 0, "p50": 40, "p90": 70, "partial": 0},
            "segments": {"measured": 3, "unmeasured": 0, "p50": 40, "p90": 70},
            "estimate": True,
        },
        "review": {
            "runs": {"measured": 8, "unmeasured": 1, "p50": 20, "p90": 35, "partial": 0},
            "segments": {"measured": 8, "unmeasured": 1, "p50": 20, "p90": 35},
            "estimate": False,
        },
    },
    "roles": {
        "<i>ada</i>": {
            "shipped": 75,
            "computed": None,
            "applied": 75,
            "segments": 6,
            "restarts": 0,
            "growth": None,
            "restart_tokens": None,
            "segment_p50": 60,
            "segment_p90": 80,
        },
        "prudence": {
            "shipped": 40,
            "computed": None,
            "applied": 40,
            "segments": 0,
            "restarts": 0,
            "growth": None,
            "restart_tokens": None,
            "segment_p50": None,
            "segment_p90": None,
        },
        "rebaser": {
            "shipped": 30,
            "computed": None,
            "applied": 30,
            "segments": 3,
            "restarts": 0,
            "growth": None,
            "restart_tokens": None,
            "segment_p50": 12,
            "segment_p90": 16,
        },
        "remi": {
            "shipped": 50,
            "computed": 64,
            "applied": 50,
            "segments": 7,
            "restarts": 3,
            "growth": 2500.4,
            "restart_tokens": 21666.6,
            "segment_p50": 40,
            "segment_p90": 64,
        },
    },
    "skipped": [],
}
CAPS_HEADER = (
    '<section class="block"><div class="block-head"><h2>Do the turn caps fit?</h2><p>The last 20 runs of each'
    ' procedure. A cap fits when 9 segments in 10 end under it.</p></div><div class="panel scroll"><table><thead>'
    '<tr><th>Role</th><th class="num">Shipped</th><th class="num">Computed</th><th class="num">Applied</th>'
    '<th class="num">Segments</th><th class="num">Restarts</th><th>p90 of a segment, against the cap</th>'
    "<th>Trend</th></tr></thead><tbody>"
)
REMI_ROW = (
    '<tr><td class="mono">remi</td><td class="num">50</td><td class="num">64</td><td class="num">50</td>'
    '<td class="num">7</td><td class="num">3</td><td>'
    '<svg class="bar" viewBox="0 0 100 8" role="img" aria-label="segment p90 64 of remi against its cap of 50">'
    '<rect class="bar-track" width="100" height="8"></rect>'
    '<rect class="bar-fill tone-limit" width="100" height="8"></rect>'
    '<line class="bar-cap" x1="78.125" y1="0" x2="78.125" y2="8"></line></svg>64 · 128 % of the cap</td><td>-</td></tr>'
)


def answer_with(document: dict) -> CommandAnswer:
    return CommandAnswer(status=200, document=json.dumps(document))


def render_overview_and_budgets() -> str:
    return render_ledger_fragment({"overview": answer_with(OVERVIEW), "budgets": answer_with(BUDGETS)})


class RenderLedgerFragmentTest(unittest.TestCase):
    def test_should_open_on_a_callout_saying_what_the_measures_cover(self):
        # Act
        fragment = render_overview_and_budgets()

        # Assert
        self.assertIn(
            '</details><div class="callout tone-faint"><p>The measures cover 5 runs finished from 2026-11-17T21:10:00Z'
            ' to 2026-11-18T09:00:00Z; 2 lines of the ledger skipped, counted in no figure.</p></div><section class="block">',
            fragment,
        )

    def test_should_say_the_measures_cover_an_empty_ledger(self):
        # Arrange
        answers = {"overview": answer_with(EMPTY_OVERVIEW), "budgets": answer_with(BUDGETS)}

        # Act
        fragment = render_ledger_fragment(answers)

        # Assert
        self.assertIn(
            '</details><div class="callout tone-faint"><p>The measures cover 0 runs finished in an empty ledger;'
            ' 0 lines of the ledger skipped, counted in no figure.</p></div><section class="block">',
            fragment,
        )

    def test_should_sort_first_the_role_whose_segment_p90_overshoots_its_cap_the_most(self):
        # Act
        fragment = render_overview_and_budgets()

        # Assert
        self.assertIn(CAPS_HEADER + REMI_ROW, fragment)

    def test_should_render_escaped_a_role_name_holding_markup(self):
        # Act
        fragment = render_overview_and_budgets()

        # Assert
        self.assertIn(
            REMI_ROW + '<tr><td class="mono">&lt;i&gt;ada&lt;/i&gt;</td><td class="num">75</td><td class="num">-</td>'
            '<td class="num">75</td><td class="num">6</td><td class="num">0</td><td>'
            '<svg class="bar" viewBox="0 0 100 8" role="img"'
            ' aria-label="segment p90 80 of &lt;i&gt;ada&lt;/i&gt; against its cap of 75">'
            '<rect class="bar-track" width="100" height="8"></rect>'
            '<rect class="bar-fill tone-limit" width="100" height="8"></rect>'
            '<line class="bar-cap" x1="93.75" y1="0" x2="93.75" y2="8"></line></svg>80 · 107 % of the cap</td>'
            "<td>-</td></tr>",
            fragment,
        )

    def test_should_mark_estimate_a_role_under_five_measured_segments(self):
        # Act
        fragment = render_overview_and_budgets()

        # Assert
        self.assertIn(
            '<tr><td class="mono">rebaser</td><td class="num">30</td><td class="num">-</td><td class="num">30</td>'
            '<td class="num">3</td><td class="num">0</td><td>'
            '<svg class="bar" viewBox="0 0 100 8" role="img" aria-label="segment p90 16 of rebaser against its cap of 30">'
            '<rect class="bar-track" width="100" height="8"></rect>'
            '<rect class="bar-fill tone-done" width="53.3333" height="8"></rect>'
            '<line class="bar-cap" x1="100" y1="0" x2="100" y2="8"></line></svg>16 · 53 % of the cap · estimate</td>'
            "<td>-</td></tr>",
            fragment,
        )

    def test_should_list_last_a_role_with_no_measured_segment_and_keep_the_table_of_the_caps(self):
        # Act
        fragment = render_overview_and_budgets()

        # Assert
        self.assertIn(
            '<tr><td class="mono">prudence</td><td class="num">40</td><td class="num">-</td><td class="num">40</td>'
            '<td class="num">0</td><td class="num">0</td><td>no segment measured</td><td>-</td></tr></tbody></table>'
            "</div></section>",
            fragment,
        )

    def test_should_give_the_turns_of_each_procedure_marked_estimate_under_five_runs(self):
        # Act
        fragment = render_overview_and_budgets()

        # Assert
        self.assertIn(
            "</figure><table><thead><tr><th>procedure</th><th>runs</th><th>p50</th><th>p90</th><th>measure</th></tr>"
            "</thead><tbody><tr><td>build-task</td><td>3</td><td>40</td><td>70</td><td>estimate</td></tr>"
            "<tr><td>review</td><td>8</td><td>20</td><td>35</td><td>measured</td></tr></tbody></table></section>",
            fragment,
        )

    def test_should_give_a_day_of_failed_actions_against_the_288_ticks_of_a_day(self):
        # Act
        fragment = render_overview_and_budgets()

        # Assert
        self.assertIn(
            "<tr><td>2026-11-18</td><td>3</td><td>"
            '<svg class="bar" viewBox="0 0 100 8" role="img" aria-label="3 failed actions for the 288 ticks of 2026-11-18">'
            '<rect class="bar-track" width="100" height="8"></rect>'
            '<rect class="bar-fill tone-failed" width="1.04167" height="8"></rect></svg></td></tr>',
            fragment,
        )

    def test_should_give_the_failed_actions_by_action_the_most_failed_first_with_its_most_frequent_error(self):
        # Act
        fragment = render_overview_and_budgets()

        # Assert
        self.assertIn(
            "<h3>By action</h3><table><thead><tr><th>action</th><th>failed</th><th>share</th>"
            "<th>most frequent error</th></tr></thead><tbody><tr><td>&lt;i&gt;LaunchTask&lt;/i&gt;</td><td>3</td><td>"
            '<svg class="bar" viewBox="0 0 100 8" role="img" aria-label="75 percent of the failed actions">'
            '<rect class="bar-track" width="100" height="8"></rect>'
            '<rect class="bar-fill tone-failed" width="75" height="8"></rect></svg></td><td>quota &lt;reached&gt;</td></tr>'
            "<tr><td>MergeWavePullRequest</td><td>1</td><td>"
            '<svg class="bar" viewBox="0 0 100 8" role="img" aria-label="25 percent of the failed actions">'
            '<rect class="bar-track" width="100" height="8"></rect>'
            '<rect class="bar-fill tone-failed" width="25" height="8"></rect></svg></td><td>not mergeable</td></tr>'
            "</tbody></table></section>",
            fragment,
        )

    def test_should_give_the_counts_of_the_overview_as_tiles(self):
        # Act
        fragment = render_overview_and_budgets()

        # Assert
        self.assertIn(
            '<section class="block"><div class="block-head"><h2>Volume</h2><p>What the ledger counts since 2026-11-17.</p>'
            '</div><div class="stat-tiles"><div class="stat-tile"><span class="stat-value">12</span>'
            '<span class="stat-label">events</span>'
            '<span class="stat-perimeter">from 2026-11-17T21:10:00Z to 2026-11-18T09:00:00Z</span></div>'
            '<div class="stat-tile"><span class="stat-value">5</span><span class="stat-label">runs finished</span>'
            '<span class="stat-perimeter">from 2026-11-17T21:10:00Z to 2026-11-18T09:00:00Z</span></div>'
            '<div class="stat-tile"><span class="stat-value">6</span><span class="stat-label">segments finished</span>'
            '<span class="stat-perimeter">from 2026-11-17T21:10:00Z to 2026-11-18T09:00:00Z</span></div>'
            '<div class="stat-tile"><span class="stat-value">2</span><span class="stat-label">waves started</span>'
            '<span class="stat-perimeter">from 2026-11-17T21:10:00Z to 2026-11-18T09:00:00Z</span></div>'
            '<div class="stat-tile"><span class="stat-value">4</span>'
            '<span class="stat-label">failed tick actions</span>'
            '<span class="stat-perimeter">from 2026-11-17T21:10:00Z to 2026-11-18T09:00:00Z</span></div></div>'
            "<h3>Waves started by month</h3>"
            "<table><thead><tr><th>month</th><th>waves</th><th>started</th><th>baseline</th></tr></thead>"
            "<tbody><tr><td>2026-11</td><td>2</td>"
            '<td><a href="#ledger?wave=w1">w1</a> <a href="#ledger?wave=%3Cb%3Ew2%3C%2Fb%3E">&lt;b&gt;w2&lt;/b&gt;</a>'
            "</td><td>-</td></tr></tbody></table></section>",
            fragment,
        )

    def test_should_link_a_month_after_the_first_day_of_the_ledger_to_its_comparison_with_the_days_before_it(self):
        # Arrange
        overview = {
            **OVERVIEW,
            "first": "2026-10-01T08:00:00Z",
            "waves_started": {"2026-10": ["w1"], "2026-11": ["w2"]},
        }

        # Act
        fragment = render_ledger_fragment({"overview": answer_with(overview), "budgets": answer_with(BUDGETS)})

        # Assert
        self.assertIn(
            '<tbody><tr><td>2026-10</td><td>1</td><td><a href="#ledger?wave=w1">w1</a></td><td>-</td></tr>'
            '<tr><td>2026-11</td><td>1</td><td><a href="#ledger?wave=w2">w2</a></td>'
            '<td><a href="#ledger?range=2026-10-01..2026-10-31&amp;range=2026-11-01..2026-11-18">'
            "compare before 2026-11-01</a></td></tr></tbody>",
            fragment,
        )

    def test_should_render_the_turns_by_role_and_the_halts_of_the_wave_asked(self):
        # Arrange
        wave = {
            "schema_version": 1,
            "wave": "<b>w2</b>",
            "ledger": {
                "turns": {
                    "by_slot": {},
                    "by_role": {
                        "<i>ada</i>": {"runs": {"measured": 2, "unmeasured": 1, "p50": 30, "p90": 50, "partial": 0}}
                    },
                },
                "halts": [
                    {
                        "halted_at": "<i>2026-10-02T10:00:00Z</i>",
                        "resumed_at": "<i>2026-10-02T11:05:00Z</i>",
                        "duration_ms": 3900000,
                    },
                    {"halted_at": "<i>2026-10-03T10:00:00Z</i>", "resumed_at": None, "duration_ms": None},
                ],
            },
        }
        answers = {"overview": answer_with(OVERVIEW), "budgets": answer_with(BUDGETS), "wave": answer_with(wave)}

        # Act
        fragment = render_ledger_fragment(answers)

        # Assert
        self.assertIn(
            "<section><h2>Turns by role and halts of the wave</h2><p>wave &lt;b&gt;w2&lt;/b&gt;</p>"
            "<table><thead><tr><th>role</th><th>runs</th><th>p50</th><th>p90</th></tr></thead>"
            "<tbody><tr><td>&lt;i&gt;ada&lt;/i&gt;</td><td>2</td><td>30</td><td>50</td></tr></tbody></table>"
            "<table><thead><tr><th>halted at</th><th>resumed at</th><th>minutes</th></tr></thead>"
            "<tbody><tr><td>&lt;i&gt;2026-10-02T10:00:00Z&lt;/i&gt;</td><td>&lt;i&gt;2026-10-02T11:05:00Z&lt;/i&gt;</td>"
            "<td>65</td></tr>"
            "<tr><td>&lt;i&gt;2026-10-03T10:00:00Z&lt;/i&gt;</td><td>still halted</td><td>-</td></tr></tbody></table>"
            "</section>",
            fragment,
        )

    def test_should_compare_two_periods_and_say_a_range_under_five_runs_is_too_small_to_compare(self):
        # Arrange
        comparison = {
            "schema_version": 1,
            "ranges": [
                {
                    "start": "<i>2026-09-01</i>",
                    "end": "2026-09-30",
                    "runs": 4,
                    "segments": 5,
                    "turns": {"runs": {"p50": 40, "p90": 80}},
                    "turns_to_first_edit": {"runs": {"p50": 6, "p90": 9}},
                    "oversized_output_turns": None,
                },
                {
                    "start": "2026-10-01",
                    "end": "2026-10-31",
                    "runs": 6,
                    "segments": 6,
                    "turns": {"runs": {"p50": 30, "p90": 45}},
                    "turns_to_first_edit": None,
                    "oversized_output_turns": None,
                },
            ],
            "reference": {},
        }
        answers = {
            "overview": answer_with(OVERVIEW),
            "budgets": answer_with(BUDGETS),
            "comparison": answer_with(comparison),
        }

        # Act
        fragment = render_ledger_fragment(answers)

        # Assert
        self.assertIn(
            "</button></form>"
            "<p>&lt;i&gt;2026-09-01&lt;/i&gt; to 2026-09-30 holds 4 runs, too small to compare:"
            " a percentile over fewer than 5 runs is an estimate.</p>"
            "<p>4 runs from &lt;i&gt;2026-09-01&lt;/i&gt; to 2026-09-30, 6 runs from 2026-10-01 to 2026-10-31</p>"
            "<table><thead><tr><th>measure</th>"
            "<th>p50 &lt;i&gt;2026-09-01&lt;/i&gt; to 2026-09-30</th><th>p90 &lt;i&gt;2026-09-01&lt;/i&gt; to 2026-09-30</th>"
            "<th>p50 2026-10-01 to 2026-10-31</th><th>p90 2026-10-01 to 2026-10-31</th></tr></thead><tbody>"
            "<tr><td>turns</td><td>40</td><td>80</td><td>30</td><td>45</td></tr>"
            "<tr><td>turns to first edit</td><td>6</td><td>9</td><td>-</td><td>-</td></tr>"
            "<tr><td>oversized output turns</td><td>-</td><td>-</td><td>-</td><td>-</td></tr>"
            "</tbody></table></section>",
            fragment,
        )

    def test_should_render_the_error_of_a_comparison_the_ledger_refused(self):
        # Arrange
        refused = CommandAnswer(status=500, document='{"error": "no run finished from 2026-09-30 to 2026-09-30\\n"}')
        answers = {"overview": answer_with(OVERVIEW), "budgets": answer_with(BUDGETS), "comparison": refused}

        # Act
        fragment = render_ledger_fragment(answers)

        # Assert
        self.assertIn(
            "</button></form><dl><dt>error</dt><dd>no run finished from 2026-09-30 to 2026-09-30\n</dd></dl></section>",
            fragment,
        )


class RenderLedgerFragmentHeadTest(unittest.TestCase):
    def test_should_open_on_the_page_head_naming_the_view_and_what_it_is_for(self):
        # Act
        fragment = render_overview_and_budgets()

        # Assert
        self.assertTrue(
            fragment.startswith(
                '<header class="page-head"><div><h1>Ledger</h1>'
                '<p class="lede">The ledger is the journal of everything brigade did. This page turns it into measures: what a run takes, whether the turn caps fit, and what keeps failing.</p></div>'
                '<p class="fresh num" data-fresh>refreshes every 5 s</p></header>'
            ),
            fragment[:300],
        )


class RenderLedgerFragmentAsTheMockupTest(unittest.TestCase):
    def test_should_say_how_to_read_the_page_in_an_explainer(self):
        # Act
        fragment = render_overview_and_budgets()

        # Assert
        self.assertIn('<details class="explainer"><summary>How to read this page</summary>', fragment)

    def test_should_answer_whether_the_caps_fit_in_one_table_whose_columns_are_named_in_words(self):
        # Act
        fragment = render_overview_and_budgets()

        # Assert
        self.assertIn(
            '<section class="block"><div class="block-head"><h2>Do the turn caps fit?</h2>'
            "<p>The last 20 runs of each procedure. A cap fits when 9 segments in 10 end under it.</p></div>",
            fragment,
        )
        self.assertIn(
            '<thead><tr><th>Role</th><th class="num">Shipped</th><th class="num">Computed</th><th class="num">Applied'
            '</th><th class="num">Segments</th><th class="num">Restarts</th><th>p90 of a segment, against the cap</th>'
            "<th>Trend</th></tr></thead>",
            fragment,
        )
        self.assertEqual(fragment.count("<th>Role</th>"), 1)

    def test_should_draw_what_a_run_takes_as_a_chart_of_its_median_and_its_90th_percentile(self):
        # Act
        fragment = render_overview_and_budgets()

        # Assert
        self.assertIn(
            '<section class="block"><div class="block-head"><h2>What a run takes</h2><p>Turns of a whole run, by'
            ' procedure: the median, and the 90th percentile.</p></div><figure class="panel pad chart"><svg',
            fragment,
        )
        self.assertIn(
            '<figcaption class="legend"><span class="tone-work">up to the median</span>'
            '<span class="tone-work soft">up to the 90th percentile</span></figcaption></figure>',
            fragment,
        )
        self.assertIn("<title>build-task: p50 40, p90 70 turns</title>", fragment)

    def test_should_draw_the_share_of_each_failing_action_as_a_bar(self):
        # Act
        fragment = render_overview_and_budgets()

        # Assert
        self.assertIn(
            '<svg class="bar" viewBox="0 0 100 8" role="img" aria-label="75 percent of the failed actions">'
            '<rect class="bar-track" width="100" height="8"></rect>'
            '<rect class="bar-fill tone-failed" width="75" height="8"></rect></svg>',
            fragment,
        )

    def test_should_band_the_volume_tiles_under_what_the_ledger_counts(self):
        # Act
        fragment = render_overview_and_budgets()

        # Assert
        self.assertIn(
            '<section class="block"><div class="block-head"><h2>Volume</h2><p>What the ledger counts since'
            ' 2026-11-17.</p></div><div class="stat-tiles">',
            fragment,
        )

    def test_should_offer_two_ranges_of_days_to_compare_with_a_compare_button(self):
        # Act
        fragment = render_overview_and_budgets()

        # Assert
        self.assertIn(
            '<section class="block"><div class="block-head"><h2>Compare two periods</h2><p>Runs finished in each'
            ' range of days, UTC.</p></div><form class="filters" data-view="ledger">'
            '<span class="field"><label for="ledger-before">Before</label><input id="ledger-before" name="range"'
            ' placeholder="2026-11-15..2026-11-17"></span>'
            '<span class="field"><label for="ledger-after">After</label><input id="ledger-after" name="range"'
            ' placeholder="2026-11-18..2026-11-18"></span><button class="btn" type="submit">Compare</button></form>',
            fragment,
        )
