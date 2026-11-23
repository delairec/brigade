import unittest

from brigade.dashboard.render_runs_fragment import RunFilters, RunsPage, render_runs_fragment

LIVE_RUN = {
    "run": "20261118T101500Z-a1b2c3",
    "procedure": "build-task",
    "slot": "build",
    "role": "ada",
    "project": "oak",
    "worktree": "/srv/oak/B94",
    "state": "running",
    "outcome": None,
    "wave": "oak_w4",
    "task": "B94",
    "started_at": "2026-11-18T10:15:00Z",
    "arguments": {"task": "@TASK.B94", "base": "integration/oak"},
    "segments": [
        {"segment": 1, "outcome": "handed_over", "turns": 80, "duration_ms": 754000},
        {"segment": 2, "outcome": None, "turns": None, "duration_ms": None},
    ],
    "duration_ms": 754000,
    "cost_usd": 1.5,
    "duration_partial": True,
    "cost_partial": True,
}
DEAD_RUN = {
    **LIVE_RUN,
    "run": "20261118T090000Z-dead01",
    "task": "B93",
    "state": "dead",
    "started_at": "2026-11-18T09:00:00Z",
}
LIMIT_CUT_RUN = {
    **LIVE_RUN,
    "run": "20261118T080000Z-c0ffee",
    "task": "B92",
    "state": "finished",
    "outcome": "turn_limit",
    "started_at": "2026-11-18T08:00:00Z",
    "segments": [{"segment": 1, "outcome": "turn_limit", "turns": 75, "duration_ms": 600000}],
    "duration_ms": 600000,
    "cost_usd": None,
    "duration_partial": False,
    "cost_partial": True,
}
DONE_RUN = {
    **LIVE_RUN,
    "run": "20261118T070000Z-d0d0d0",
    "procedure": "vibe",
    "wave": None,
    "task": None,
    "state": "finished",
    "outcome": "done",
    "started_at": "2026-11-18T07:00:00Z",
    "arguments": {},
    "segments": [
        {"segment": 1, "outcome": "wall_limit", "turns": 30, "duration_ms": 1500000},
        {"segment": 2, "outcome": "done", "turns": 12, "duration_ms": 600000},
    ],
    "duration_ms": 2100000,
    "cost_usd": 1.75,
    "duration_partial": False,
    "cost_partial": False,
}
STARTING_RUN = {
    **LIVE_RUN,
    "run": "20261118T110000Z-5ta7e0",
    "arguments": {},
    "segments": [],
    "duration_ms": None,
    "cost_usd": None,
    "duration_partial": False,
    "cost_partial": False,
}
NO_FILTER = RunFilters(state=None, wave=None, task=None)
NOTHING_SKIPPED = []


def create_listing(runs: list[dict], skipped: list[dict]) -> dict:
    return {"schema_version": 1, "runs": runs, "skipped": skipped}


def create_page(listing: dict, filters: RunFilters) -> RunsPage:
    return RunsPage(listing=listing, every_run=listing, filters=filters)


class RenderRunsFragmentTest(unittest.TestCase):
    def test_should_count_the_live_runs_the_finished_ones_with_their_outcomes_and_the_dead_ones(self):
        # Arrange
        listing = create_listing([LIVE_RUN, DEAD_RUN, LIMIT_CUT_RUN, DONE_RUN], NOTHING_SKIPPED)

        # Act
        fragment = render_runs_fragment(create_page(listing, NO_FILTER))

        # Assert
        self.assertIn(
            '<div class="stat-tiles">'
            '<div class="stat-tile"><span class="stat-value">1</span><span class="stat-label">live</span>'
            '<span class="stat-perimeter">of 4 runs listed</span></div>'
            '<div class="stat-tile"><span class="stat-value">2</span><span class="stat-label">finished</span>'
            '<span class="stat-perimeter">1 done · 1 turn limit</span></div>'
            '<div class="stat-tile"><span class="stat-value">1</span><span class="stat-label">dead</span>'
            '<span class="stat-perimeter">runs whose process ended without a result</span></div>'
            '<div class="stat-tile"><span class="stat-value">70m08s</span><span class="stat-label">run time</span>'
            '<span class="stat-perimeter">over the segments that ended</span></div>'
            '<div class="stat-tile"><span class="stat-value">at least $4.75</span><span class="stat-label">cost</span>'
            '<span class="stat-perimeter">over the runs listed; runs lacking a cost: 3</span></div>'
            "</div>",
            fragment,
        )

    def test_should_say_how_many_run_directories_the_list_skipped(self):
        # Arrange
        skipped = [{"run": "by-hand", "reason": "refused"}, {"run": "other", "reason": "refused"}]
        listing = create_listing([LIVE_RUN], skipped)

        # Act
        fragment = render_runs_fragment(create_page(listing, NO_FILTER))

        # Assert
        self.assertIn('<p class="skipped">The list skipped 2 run directories it could not read.</p>', fragment)

    def test_should_show_a_run_outside_a_wave_and_a_task_with_a_dash(self):
        # Arrange
        listing = create_listing([DONE_RUN], NOTHING_SKIPPED)

        # Act
        fragment = render_runs_fragment(create_page(listing, NO_FILTER))

        # Assert
        self.assertIn("<td>vibe</td><td>ada</td><td>-</td>", fragment)

    def test_should_say_no_run_matches_when_the_list_is_empty(self):
        # Arrange
        no_run = []
        listing = create_listing(no_run, NOTHING_SKIPPED)

        # Act
        fragment = render_runs_fragment(create_page(listing, NO_FILTER))

        # Assert
        self.assertIn(
            '<div class="empty-state"><p class="empty-why">No run matches these filters.</p>'
            '<p class="empty-fill">A run appears here once the tick or brigade run starts a procedure.</p></div>',
            fragment,
        )

    def test_should_escape_the_strings_of_a_run(self):
        # Arrange
        markup = "<script>alert(1)</script>"
        run = {**LIVE_RUN, "run": markup, "procedure": markup, "task": markup, "wave": markup}
        listing = create_listing([run], NOTHING_SKIPPED)

        # Act
        fragment = render_runs_fragment(create_page(listing, RunFilters(state=None, wave=markup, task=markup)))

        # Assert
        self.assertNotIn("<script>", fragment)


class RenderRunsFragmentHeadTest(unittest.TestCase):
    def test_should_open_on_the_page_head_naming_the_view_and_what_it_is_for(self):
        # Act
        fragment = render_runs_fragment(create_page(create_listing([LIVE_RUN], NOTHING_SKIPPED), NO_FILTER))

        # Assert
        self.assertTrue(
            fragment.startswith(
                '<header class="page-head"><div><h1>Runs</h1>'
                '<p class="lede">A run is one agent at work: a procedure, such as a build or a review, played by a role on a task.</p></div>'
                '<p class="fresh num" data-fresh>refreshes every 5 s</p></header>'
            ),
            fragment[:300],
        )


RUNNING_PILL = '<span class="pill"><span class="tone tone-work"><span class="tone-shape" aria-hidden="true">●</span>running</span></span>'


class RenderRunsFragmentAsTheMockupTest(unittest.TestCase):
    def test_should_say_how_to_read_the_page_in_an_explainer_folded_by_default(self):
        # Act
        fragment = render_runs_fragment(create_page(create_listing([LIVE_RUN], NOTHING_SKIPPED), NO_FILTER))

        # Assert
        self.assertIn('<details class="explainer"><summary>How to read this page</summary>', fragment)

    def test_should_list_every_run_in_one_table_the_newest_first_by_its_short_start_and_short_id(self):
        # Arrange
        listing = create_listing([DONE_RUN, LIMIT_CUT_RUN, DEAD_RUN, LIVE_RUN], NOTHING_SKIPPED)

        # Act
        fragment = render_runs_fragment(create_page(listing, NO_FILTER))

        # Assert
        self.assertIn(
            "<thead><tr><th>Started</th><th>Run</th><th>Procedure</th><th>Role</th><th>Task</th><th>Outcome</th>"
            '<th>Segments</th><th class="num">Duration</th><th class="num">Cost</th><th>Arguments</th>'
            "</tr></thead><tbody>"
            '<tr><td class="num">11-18 10:15Z</td><td><a class="mono" href="#runs/20261118T101500Z-a1b2c3"'
            ' title="20261118T101500Z-a1b2c3">…101500Z-a1b2c3</a></td><td>build-task</td><td>ada</td>'
            f'<td><a class="mono" href="#waves/oak_w4">B94</a></td><td>{RUNNING_PILL}</td>'
            '<td><span class="segment-squares" role="img" aria-label="segments: handed_over, running">'
            '<span class="segment-square tone-faint" title="handed_over"></span>'
            '<span class="segment-square tone-work" title="running"></span></span></td>'
            '<td class="num">at least 12m34s</td><td class="num">at least $1.50</td>'
            '<td class="mono">base=integration/oak task=@TASK.B94</td></tr>'
            '<tr><td class="num">11-18 09:00Z</td>',
            fragment,
        )
        self.assertLess(fragment.index("…090000Z-dead01"), fragment.index("…080000Z-c0ffee"))
        self.assertLess(fragment.index("…080000Z-c0ffee"), fragment.index("…070000Z-d0d0d0"))

    def test_should_count_the_runs_of_each_state_on_its_chip(self):
        # Arrange
        listing = create_listing([LIVE_RUN, DEAD_RUN, LIMIT_CUT_RUN, DONE_RUN], NOTHING_SKIPPED)

        # Act
        fragment = render_runs_fragment(create_page(listing, NO_FILTER))

        # Assert
        self.assertIn(
            '<nav class="chips"><a class="chip" href="#runs" aria-current="true">All <b>4</b></a>'
            '<a class="chip" href="#runs?state=running">Running <b>1</b></a>'
            '<a class="chip" href="#runs?state=finished">Finished <b>2</b></a>'
            '<a class="chip" href="#runs?state=dead">Dead <b>1</b></a></nav>',
            fragment,
        )

    def test_should_give_each_choice_of_a_selector_the_address_it_leads_to_keeping_the_other_choices(self):
        # Arrange
        listing = create_listing([LIVE_RUN, LIMIT_CUT_RUN], NOTHING_SKIPPED)
        filters = RunFilters(state="running", wave=None, task="B94")

        # Act
        fragment = render_runs_fragment(create_page(listing, filters))

        # Assert
        self.assertIn(
            '<div class="filters"><span class="field"><label for="runs-wave">Wave</label>'
            '<select id="runs-wave" name="wave"><option value="" data-href="runs?state=running&amp;task=B94"'
            ' selected>any</option><option value="oak_w4" data-href="runs?state=running&amp;wave=oak_w4&amp;task=B94">'
            "oak_w4</option></select></span>"
            '<span class="field"><label for="runs-task">Task</label><select id="runs-task" name="task">'
            '<option value="" data-href="runs?state=running">any</option>'
            '<option value="B92" data-href="runs?state=running&amp;task=B92">B92</option>'
            '<option value="B94" data-href="runs?state=running&amp;task=B94" selected>B94</option>'
            "</select></span></div>",
            fragment,
        )

    def test_should_name_the_task_of_a_run_of_no_wave_without_a_link(self):
        # Arrange
        run_of_no_wave = {**DONE_RUN, "task": "B95"}

        # Act
        fragment = render_runs_fragment(create_page(create_listing([run_of_no_wave], NOTHING_SKIPPED), NO_FILTER))

        # Assert
        self.assertIn('<td><span class="mono">B95</span></td>', fragment)


W5_RUN = {**LIVE_RUN, "run": "20261118T060000Z-e5e5e5", "wave": "oak_w5", "task": "B97", "state": "dead"}


class RenderRunsFragmentSelectorsTest(unittest.TestCase):
    def test_should_offer_the_waves_and_the_tasks_of_every_run_kept_not_only_of_the_runs_listed(self):
        # Arrange
        listed = create_listing([LIVE_RUN], NOTHING_SKIPPED)
        every_run = create_listing([LIVE_RUN, W5_RUN], NOTHING_SKIPPED)
        filters = RunFilters(state=None, wave="oak_w4", task=None)

        # Act
        fragment = render_runs_fragment(RunsPage(listing=listed, every_run=every_run, filters=filters))

        # Assert
        self.assertIn(
            '<select id="runs-wave" name="wave"><option value="" data-href="runs">any</option>'
            '<option value="oak_w4" data-href="runs?wave=oak_w4" selected>oak_w4</option>'
            '<option value="oak_w5" data-href="runs?wave=oak_w5">oak_w5</option></select>',
            fragment,
        )
        self.assertIn('<option value="B97" data-href="runs?wave=oak_w4&amp;task=B97">B97</option>', fragment)

    def test_should_keep_selected_the_wave_in_force_when_no_run_kept_holds_it(self):
        # Arrange
        nothing_listed = create_listing([], NOTHING_SKIPPED)
        every_run = create_listing([LIVE_RUN], NOTHING_SKIPPED)
        filters = RunFilters(state=None, wave="oak_w1", task=None)

        # Act
        fragment = render_runs_fragment(RunsPage(listing=nothing_listed, every_run=every_run, filters=filters))

        # Assert
        self.assertIn(
            '<select id="runs-wave" name="wave"><option value="" data-href="runs">any</option>'
            '<option value="oak_w1" data-href="runs?wave=oak_w1" selected>oak_w1</option>'
            '<option value="oak_w4" data-href="runs?wave=oak_w4">oak_w4</option></select>',
            fragment,
        )


class RenderRunsFragmentOfRunsThatWentWrongTest(unittest.TestCase):
    def test_should_name_the_runs_a_limit_cut_by_procedure_and_limit_with_the_latest_of_them(self):
        # Arrange
        later_limit_cut_run = {
            **LIMIT_CUT_RUN,
            "run": "20261118T083000Z-c0ffe2",
            "task": "B91",
            "started_at": "2026-11-18T08:30:00Z",
        }
        listing = create_listing([LIVE_RUN, LIMIT_CUT_RUN, later_limit_cut_run, DONE_RUN], [])

        # Act
        fragment = render_runs_fragment(create_page(listing, NO_FILTER))

        # Assert
        self.assertIn(
            "<p>2 build-task runs were cut at the turn limit, the latest 20261118T083000Z-c0ffe2 on B91.</p></div>",
            fragment,
        )

    def test_should_name_the_dead_runs_with_the_latest_of_them(self):
        # Arrange
        listing = create_listing([LIVE_RUN, DEAD_RUN, DONE_RUN], [])

        # Act
        fragment = render_runs_fragment(create_page(listing, NO_FILTER))

        # Assert
        self.assertIn(
            "<p>1 run is dead, its process gone without a result: the latest 20261118T090000Z-dead01 on B93.</p></div>",
            fragment,
        )


class RenderRunsFragmentMeasuresTest(unittest.TestCase):
    def test_should_show_the_strip_of_a_run_cut_then_done_and_its_whole_measures(self):
        # Arrange
        listing = create_listing([DONE_RUN], NOTHING_SKIPPED)

        # Act
        fragment = render_runs_fragment(create_page(listing, NO_FILTER))

        # Assert
        self.assertIn(
            '<td><span class="segment-squares" role="img" aria-label="segments: wall_limit, done">'
            '<span class="segment-square tone-limit" title="wall_limit"></span>'
            '<span class="segment-square tone-done" title="done"></span></span></td>'
            '<td class="num">35m00s</td><td class="num">$1.75</td><td class="mono">-</td>',
            fragment,
        )

    def test_should_render_an_argument_holding_markup_escaped(self):
        # Arrange
        run = {**DONE_RUN, "arguments": {"base": "<script>alert(1)</script>"}}
        listing = create_listing([run], NOTHING_SKIPPED)

        # Act
        fragment = render_runs_fragment(create_page(listing, NO_FILTER))

        # Assert
        self.assertIn('<td class="mono">base=&lt;script&gt;alert(1)&lt;/script&gt;</td>', fragment)

    def test_should_show_a_dash_for_the_measures_of_a_run_starting_its_first_segment(self):
        # Arrange
        listing = create_listing([STARTING_RUN], NOTHING_SKIPPED)

        # Act
        fragment = render_runs_fragment(create_page(listing, NO_FILTER))

        # Assert
        self.assertIn(
            '<td><span class="segment-squares" role="img" aria-label="segments: running">'
            '<span class="segment-square tone-work" title="running"></span></span></td>'
            '<td class="num">-</td><td class="num">-</td><td class="mono">-</td>',
            fragment,
        )

    def test_should_total_the_cost_as_a_floor_when_a_run_records_no_cost_yet(self):
        # Arrange
        listing = create_listing([STARTING_RUN], NOTHING_SKIPPED)

        # Act
        fragment = render_runs_fragment(create_page(listing, NO_FILTER))

        # Assert
        self.assertIn(
            '<div class="stat-tile"><span class="stat-value">0m00s</span><span class="stat-label">run time</span>'
            '<span class="stat-perimeter">over the segments that ended</span></div>'
            '<div class="stat-tile"><span class="stat-value">at least $0.00</span><span class="stat-label">cost</span>'
            '<span class="stat-perimeter">over the runs listed; runs lacking a cost: 1</span></div>',
            fragment,
        )


class RenderRunsFragmentCostTest(unittest.TestCase):
    def test_should_say_where_the_cost_went_by_procedure_marked_a_floor_where_a_run_records_none(self):
        # Arrange
        listing = create_listing([LIVE_RUN, DEAD_RUN, LIMIT_CUT_RUN, DONE_RUN], NOTHING_SKIPPED)

        # Act
        fragment = render_runs_fragment(create_page(listing, NO_FILTER))

        # Assert
        self.assertIn(
            '<section class="block"><div class="block-head"><h2>Where the cost went</h2>'
            "<p>The 4 runs listed, by procedure.</p></div>"
            "<table><thead><tr><th>procedure</th><th>runs</th><th>cost</th></tr></thead><tbody>"
            "<tr><td>build-task</td><td>3</td><td>at least $3.00</td></tr>"
            "<tr><td>vibe</td><td>1</td><td>$1.75</td></tr></tbody></table></section>",
            fragment,
        )

    def test_should_leave_out_where_the_cost_went_when_no_run_matches(self):
        # Arrange
        no_run = []
        listing = create_listing(no_run, NOTHING_SKIPPED)

        # Act
        fragment = render_runs_fragment(create_page(listing, NO_FILTER))

        # Assert
        self.assertNotIn("<h2>Where the cost went</h2>", fragment)
