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
        "title": None,
    }


def create_run_finished(run: str, cost_usd: float | None) -> dict:
    recorded_cost = {} if cost_usd is None else {"cost_usd": cost_usd}
    return {
        "at": "2026-10-01T09:30:00Z",
        "event": "run.finished",
        "fields": {"run": run, "slot": "build", "wave": "oak_w5", "task": "OK8", "main_turns": 52, **recorded_cost},
    }


def create_wave(
    costless_runs: tuple[dict, ...] = (), states: tuple[str, str] = ("merged", "merged"), unmeasured_runs: int = 0
) -> dict:
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
            "events": [
                create_run_finished("r1", 6.85),
                create_run_finished("r2", 1.15),
                create_run_finished("r2", 0.0),
                *costless_runs,
            ],
        },
    }


def create_unrecorded_wave() -> dict:
    wave = create_wave()
    ledger = {
        **wave["ledger"],
        "cost_usd": None,
        "by_task": [
            {"task": "OK7", "turns": None, "partial": False, "duration_ms": None, "cost_usd": None},
            {"task": "OK8", "turns": None, "partial": False, "duration_ms": None, "cost_usd": None},
        ],
        "turns": {"by_slot": {}},
        "turns_by_task": {},
        "events": [],
    }
    return {**wave, "ledger": ledger}


def render(fields: list[dict], waves: list[dict] = NO_WAVE, address: str | None = NO_FORGE) -> str:
    return render_report_fragment(ReportReading(create_document(fields), waves, address))


MERGED_2_OF_2 = (
    '<span class="pill"><span class="tone tone-done"><span class="tone-shape" aria-hidden="true">✓</span>'
    "2 of 2 merged</span></span>"
)
REPORT_FIELDS = [
    {"name": "MILESTONE", "value": "M4"},
    {"name": "PROJECT", "value": "oak"},
    {"name": "TASK_ROW", "value": "OK7 merged #52 #41"},
    {"name": "TASK_ROW", "value": "OK8 merged #53"},
    {"name": "STATISTIC", "value": "tasks 2"},
    {"name": "STATISTIC", "value": "merged 2"},
    {"name": "GRAPH", "value": "OK8 after OK7"},
    {"name": "MANUAL_TEST", "value": "OK7: the command prints its table"},
    {"name": "NARRATIVE", "value": "M4 delivered its two tasks in oak_w5, none parked."},
    {"name": "NARRATIVE", "value": "Cost read from run.finished: 8.00 USD."},
    {"name": "NARRATIVE", "value": "What went wrong: OK7 needed three rounds."},
    {"name": "NARRATIVE", "value": "What went well: OK8 passed at once."},
    {"name": "NARRATIVE", "value": "Next milestone should change: review the rebase first."},
    {"name": "REASON", "value": "No task of M4 was parked."},
    {"name": "TESTER_STEP", "value": "OK7: run the command and read its table"},
    {"name": "TESTER_STEP", "value": "OK7: run it again"},
    {"name": "TESTER_STEP", "value": "run the unit tests"},
    {"name": "SAMPLING", "value": "oak/table.py (OK7, #52): read the widths"},
    {"name": "INSTRUCTIONS_CHANGE", "value": "corpus/tasks.awawa +3 -0"},
]


def create_ledgered_wave() -> dict:
    wave = create_wave()
    return {
        **wave,
        "ledger": {
            **wave["ledger"],
            "pull_requests": [{"task": "OK7", "pr": 52, "rounds": 3}],
            "rounds_by_task": {"OK8": 1},
        },
    }


class TilesTest(unittest.TestCase):
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
            '<div class="stat-tile"><span class="stat-value">2 runs, 127 turns</span><span class="stat-label">runs</span>'
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
        fragment = render(
            fields, [create_wave(costless_runs=(create_run_finished("r3", None), create_run_finished("r4", None)))]
        )

        # Assert
        self.assertIn(
            '<span class="stat-value">41.28 USD</span><span class="stat-label">cost</span>'
            '<span class="stat-perimeter">a floor: 2 runs record no cost</span>',
            fragment,
        )

    def test_should_leave_the_cost_unmarked_when_every_run_records_one_whatever_its_turns(self):
        # Arrange
        fields = [{"name": "STATISTIC", "value": "files 12"}]

        # Act
        fragment = render(fields, [create_wave(unmeasured_runs=2)])

        # Assert
        self.assertIn(
            '<span class="stat-value">41.28 USD</span><span class="stat-label">cost</span>'
            '<span class="stat-perimeter">the waves oak_w5</span>',
            fragment,
        )

    def test_should_say_the_cost_and_the_run_time_not_recorded_when_no_run_records_them(self):
        # Arrange
        fields = [{"name": "STATISTIC", "value": "files 12"}]

        # Act
        fragment = render(fields, [create_unrecorded_wave()])

        # Assert
        self.assertIn(
            '<span class="stat-value">not recorded</span><span class="stat-label">cost</span>'
            '<span class="stat-perimeter">the waves oak_w5</span></div>'
            '<div class="stat-tile"><span class="stat-value">4 h 50 min</span><span class="stat-label">wall time</span>'
            '<span class="stat-perimeter">run time not recorded</span>',
            fragment,
        )

    def test_should_sum_the_cost_and_the_run_time_of_the_waves_that_record_them(self):
        # Arrange
        fields = [{"name": "STATISTIC", "value": "files 12"}]

        # Act
        fragment = render(fields, [create_wave(), {**create_unrecorded_wave(), "wave": "oak_w6"}])

        # Assert
        self.assertIn(
            '<span class="stat-value">41.28 USD</span><span class="stat-label">cost</span>'
            '<span class="stat-perimeter">the waves oak_w5, oak_w6</span></div>'
            '<div class="stat-tile"><span class="stat-value">9 h 40 min</span><span class="stat-label">wall time</span>'
            '<span class="stat-perimeter">50 min of run time</span>',
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


class MockupTest(unittest.TestCase):
    def test_should_name_the_milestone_with_how_much_it_merged_and_read_its_verdict_as_the_lede(self):
        # Act
        fragment = render(REPORT_FIELDS, [create_ledgered_wave()], "https://github.com/acme/oak/pull/")

        # Assert
        self.assertTrue(
            fragment.startswith(
                '<header class="page-head"><div><p class="crumbs"><a href="#reports">Reports</a> / oak /'
                f' milestone report</p><h1>Milestone <span class="mono">M4</span> {MERGED_2_OF_2}</h1>'
                '<p class="lede">M4 delivered its two tasks in oak_w5, none parked.</p></div>'
                '<p class="fresh">body of <a href="https://github.com/acme/oak/pull/57">pull request #57</a>,'
                " reported 2026-10-03</p></header>"
            )
        )

    def test_should_give_the_milestone_its_title_after_its_name(self):
        # Arrange
        document = {**create_document(REPORT_FIELDS), "title": "Checkout"}

        # Act
        fragment = render_report_fragment(ReportReading(document, [create_ledgered_wave()], NO_FORGE))

        # Assert
        self.assertIn(f'<h1>Milestone <span class="mono">M4</span> · Checkout {MERGED_2_OF_2}</h1>', fragment)

    def test_should_take_the_verdict_a_line_names_as_such_without_its_label(self):
        # Arrange
        fields = [
            {"name": "NARRATIVE", "value": "Cost: 8 USD."},
            {"name": "NARRATIVE", "value": "Verdict: M4 is delivered."},
        ]

        # Act
        fragment = render(fields)

        # Assert
        self.assertIn('<p class="lede">M4 is delivered.</p>', fragment)

    def test_should_set_what_went_wrong_beside_what_went_well_and_what_to_change_each_without_its_label(self):
        # Act
        fragment = render(REPORT_FIELDS, [create_ledgered_wave()])

        # Assert
        self.assertIn(
            '<div class="split"><section class="block"><div class="block-head"><h2>Went wrong</h2><p>1 line</p></div>'
            '<ul class="panel lines"><li><p><a href="#waves/oak_w5">OK7</a> needed three rounds.</p></li></ul>'
            '</section><div class="block"><section class="block"><div class="block-head"><h2>Went well</h2>'
            '<p>1 line</p></div><ul class="panel lines"><li><p><a href="#waves/oak_w5">OK8</a> passed at once.</p></li>'
            '</ul></section><section class="block"><div class="block-head"><h2>For the next wave</h2><p>1 line</p>'
            '</div><ul class="panel lines"><li><p>review the rebase first.</p></li></ul></section></div></div>',
            fragment,
        )

    def test_should_draw_one_table_of_the_tasks_with_their_pull_requests_what_they_follow_their_rounds_and_cost(self):
        # Act
        fragment = render(REPORT_FIELDS, [create_ledgered_wave()], "https://github.com/acme/oak/pull/")

        # Assert
        self.assertIn(
            '<section class="block"><div class="block-head"><h2>Tasks</h2><p>What the milestone delivered, and in'
            ' what order.</p></div><div class="panel scroll"><table><thead><tr><th>Task</th><th>State</th>'
            '<th>Pull requests</th><th>Comes after</th><th class="num">Review rounds</th><th class="num">Cost</th>'
            "</tr></thead><tbody>"
            '<tr><td><a class="mono" href="#waves/oak_w5">OK7</a></td><td><span class="pill"><span class="tone'
            ' tone-done"><span class="tone-shape" aria-hidden="true">✓</span>merged</span></span></td>'
            '<td><a href="https://github.com/acme/oak/pull/52">#52</a> <span class="muted">· #41</span></td>'
            '<td class="muted">-</td><td class="num flag">3</td><td class="num">6.85</td></tr>'
            '<tr><td><a class="mono" href="#waves/oak_w5">OK8</a></td><td><span class="pill"><span class="tone'
            ' tone-done"><span class="tone-shape" aria-hidden="true">✓</span>merged</span></span></td>'
            '<td><a href="https://github.com/acme/oak/pull/53">#53</a></td>'
            '<td class="mono">OK7</td><td class="num">1</td><td class="num">1.15</td></tr>'
            '</tbody></table><p class="cap">Rounds and cost come from the ledger of the waves oak_w5.</p></div></section>',
            fragment,
        )

    def test_should_fold_the_tester_steps_by_task_as_numbered_steps(self):
        # Act
        fragment = render(REPORT_FIELDS, [create_ledgered_wave()])

        # Assert
        self.assertIn(
            '<section class="block"><div class="block-head"><h2>Test it by hand</h2><p>3 steps in a tester\'s words,'
            ' by task. Do these before you trust the merge.</p></div><div class="panel">'
            '<details class="fold"><summary>OK7 <span>· 2 steps</span></summary><ol class="steps">'
            "<li><p>run the command and read its table</p></li><li><p>run it again</p></li></ol></details>"
            '<details class="fold"><summary>Every task <span>· 1 step</span></summary><ol class="steps">'
            "<li><p>run the unit tests</p></li></ol></details></div></section>",
            fragment,
        )

    def test_should_list_why_a_task_was_held_and_the_code_worth_reading_tagged_by_task(self):
        # Act
        fragment = render(REPORT_FIELDS, [create_ledgered_wave()])

        # Assert
        self.assertIn(
            '<section class="block"><div class="block-head"><h2>Why a task was held</h2><p>1 reason.</p></div>'
            '<ul class="panel lines"><li><p>No task of M4 was parked.</p></li></ul></section>'
            '<section class="block"><div class="block-head"><h2>Worth reading in the code</h2><p>1 place the'
            ' reporter picked for a review by sampling.</p></div><ul class="panel lines"><li><p><span class="tag">'
            'OK7</span>oak/table.py (<a href="#waves/oak_w5">OK7</a>, #52): read the widths</p></li></ul></section>',
            fragment,
        )

    def test_should_fold_everything_else_the_report_holds_in_the_full_account(self):
        # Act
        fragment = render(REPORT_FIELDS, [create_ledgered_wave()])

        # Assert
        self.assertIn(
            '<section class="block"><div class="block-head"><h2>The full account</h2><p>Everything else the report'
            ' holds, as written.</p></div><div class="panel">'
            '<details class="fold"><summary>What happened <span>· 1 narrative line</span></summary>'
            '<ul class="lines"><li><p>Cost read from run.finished: 8.00 USD.</p></li></ul></details>'
            '<details class="fold"><summary>The SPEC lines to test <span>· 1 line</span></summary>'
            '<ul class="lines"><li><p><a href="#waves/oak_w5">OK7</a>: the command prints its table</p></li></ul></details>'
            '<details class="fold"><summary>Statistics as the CLI filled them <span>· tasks 2 · merged 2</span>'
            "</summary></details>"
            '<details class="fold"><summary>Other fields <span>· INSTRUCTIONS_CHANGE</span></summary>'
            '<dl class="panel pad kv"><div><dt>INSTRUCTIONS_CHANGE</dt><dd>corpus/tasks.awawa +3 -0</dd></div></dl>'
            "</details></div></section>",
            fragment,
        )

    def test_should_name_a_report_of_no_milestone_by_its_id(self):
        # Arrange
        document = create_document([])
        document["report"]["kind"] = "wave-report"
        document["report"]["id"] = "oak_w3"

        # Act
        fragment = render_report_fragment(ReportReading(document, NO_WAVE, NO_FORGE))

        # Assert
        self.assertIn(
            '<p class="crumbs"><a href="#reports">Reports</a> / oak / wave report</p><h1>Report <span class="mono">'
            "oak_w3</span></h1>",
            fragment,
        )


class LedgerLacksTest(unittest.TestCase):
    def test_should_say_the_report_is_the_body_of_no_pull_request_when_none_is_recorded(self):
        # Arrange
        document = {**create_document(REPORT_FIELDS), "pull_request": None}

        # Act
        fragment = render_report_fragment(ReportReading(document, NO_WAVE, NO_FORGE))

        # Assert
        self.assertIn('<p class="fresh">reported 2026-10-03</p></header>', fragment)

    def test_should_give_no_rounds_and_no_cost_to_a_task_of_no_wave_read(self):
        # Act
        fragment = render(REPORT_FIELDS, NO_WAVE)

        # Assert
        self.assertIn('<td class="muted">-</td><td class="num">-</td><td class="num">-</td></tr>', fragment)

    def test_should_link_a_run_and_leave_a_pull_request_unlinked_off_a_forge_in_a_line_of_the_report(self):
        # Arrange
        fields = [{"name": "REASON", "value": "OK7 stopped in 20261001T090000Z-a1, see #52"}]

        # Act
        fragment = render(fields, [create_ledgered_wave()])

        # Assert
        self.assertIn(
            '<li><p><a href="#waves/oak_w5">OK7</a> stopped in <a href="#runs/20261001T090000Z-a1">'
            "20261001T090000Z-a1</a>, see #52</p></li>",
            fragment,
        )

    def test_should_escape_a_value_holding_markup(self):
        # Arrange
        markup = "<script>alert(1)</script>"
        fields = [
            {"name": "NARRATIVE", "value": markup},
            {"name": "TASK_ROW", "value": markup},
            {"name": "REASON", "value": markup},
            {"name": "TESTER_STEP", "value": markup},
            {"name": "SAMPLING", "value": markup},
            {"name": "OTHER", "value": markup},
        ]

        # Act
        fragment = render(fields, [create_ledgered_wave()])

        # Assert
        self.assertNotIn("<script>", fragment)

    def test_should_leave_out_a_block_the_report_holds_nothing_for(self):
        # Arrange
        fields = [{"name": "NARRATIVE", "value": "Verdict: delivered."}]

        # Act
        fragment = render(fields)

        # Assert
        self.assertNotIn("<h2>Went wrong</h2>", fragment)
        self.assertNotIn("<h2>Tasks</h2>", fragment)
        self.assertNotIn("<h2>Test it by hand</h2>", fragment)
