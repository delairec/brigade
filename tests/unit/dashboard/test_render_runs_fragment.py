import unittest

from brigade.dashboard.render_runs_fragment import RunFilters, render_runs_fragment

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
}
NO_FILTER = RunFilters(state=None, wave=None, task=None)
NOTHING_SKIPPED = []


def create_listing(runs: list[dict], skipped: list[dict]) -> dict:
    return {"schema_version": 1, "runs": runs, "skipped": skipped}


class RenderRunsFragmentTest(unittest.TestCase):
    def test_should_count_the_live_runs_the_finished_ones_by_outcome_and_the_dead_ones(self):
        # Arrange
        listing = create_listing([LIVE_RUN, DEAD_RUN, LIMIT_CUT_RUN, DONE_RUN], NOTHING_SKIPPED)

        # Act
        fragment = render_runs_fragment(listing, NO_FILTER)

        # Assert
        self.assertIn(
            '<div class="stat-tiles">'
            '<div class="stat-tile"><span class="stat-value">1</span><span class="stat-label">live</span>'
            '<span class="stat-perimeter">runs whose process is alive</span></div>'
            '<div class="stat-tile"><span class="stat-value">1</span><span class="stat-label">done</span>'
            '<span class="stat-perimeter">runs finished on this outcome</span></div>'
            '<div class="stat-tile"><span class="stat-value">1</span><span class="stat-label">turn_limit</span>'
            '<span class="stat-perimeter">runs finished on this outcome</span></div>'
            '<div class="stat-tile"><span class="stat-value">1</span><span class="stat-label">dead</span>'
            '<span class="stat-perimeter">runs whose process ended without a result</span></div>'
            "</div>",
            fragment,
        )

    def test_should_say_how_many_run_directories_the_list_skipped(self):
        # Arrange
        skipped = [{"run": "by-hand", "reason": "refused"}, {"run": "other", "reason": "refused"}]
        listing = create_listing([LIVE_RUN], skipped)

        # Act
        fragment = render_runs_fragment(listing, NO_FILTER)

        # Assert
        self.assertIn('<p class="skipped">The list skipped 2 run directories it could not read.</p>', fragment)

    def test_should_show_a_run_outside_a_wave_and_a_task_with_a_dash(self):
        # Arrange
        listing = create_listing([DONE_RUN], NOTHING_SKIPPED)

        # Act
        fragment = render_runs_fragment(listing, NO_FILTER)

        # Assert
        self.assertIn("<td>vibe</td><td>ada</td><td>-</td>", fragment)

    def test_should_say_no_run_matches_when_the_list_is_empty(self):
        # Arrange
        no_run = []
        listing = create_listing(no_run, NOTHING_SKIPPED)

        # Act
        fragment = render_runs_fragment(listing, NO_FILTER)

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
        fragment = render_runs_fragment(listing, RunFilters(state=None, wave=markup, task=markup))

        # Assert
        self.assertNotIn("<script>", fragment)


class RenderRunsFragmentHeadTest(unittest.TestCase):
    def test_should_open_on_the_page_head_naming_the_view_and_what_it_is_for(self):
        # Act
        fragment = render_runs_fragment(create_listing([LIVE_RUN], NOTHING_SKIPPED), NO_FILTER)

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
        fragment = render_runs_fragment(create_listing([LIVE_RUN], NOTHING_SKIPPED), NO_FILTER)

        # Assert
        self.assertIn('<details class="explainer"><summary>How to read this page</summary>', fragment)

    def test_should_list_every_run_in_one_table_the_newest_first_by_its_short_start_and_short_id(self):
        # Arrange
        listing = create_listing([DONE_RUN, LIMIT_CUT_RUN, DEAD_RUN, LIVE_RUN], NOTHING_SKIPPED)

        # Act
        fragment = render_runs_fragment(listing, NO_FILTER)

        # Assert
        self.assertIn(
            "<thead><tr><th>Started</th><th>Run</th><th>Procedure</th><th>Role</th><th>Task</th><th>Outcome</th>"
            "</tr></thead><tbody>"
            '<tr><td class="num">11-18 10:15Z</td><td><a class="mono" href="#runs/20261118T101500Z-a1b2c3"'
            ' title="20261118T101500Z-a1b2c3">…101500Z-a1b2c3</a></td><td>build-task</td><td>ada</td>'
            f'<td><a class="mono" href="#waves/oak_w4">B94</a></td><td>{RUNNING_PILL}</td></tr>'
            '<tr><td class="num">11-18 09:00Z</td>',
            fragment,
        )
        self.assertLess(fragment.index("…090000Z-dead01"), fragment.index("…080000Z-c0ffee"))
        self.assertLess(fragment.index("…080000Z-c0ffee"), fragment.index("…070000Z-d0d0d0"))

    def test_should_count_the_runs_of_each_state_on_its_chip(self):
        # Arrange
        listing = create_listing([LIVE_RUN, DEAD_RUN, LIMIT_CUT_RUN, DONE_RUN], NOTHING_SKIPPED)

        # Act
        fragment = render_runs_fragment(listing, NO_FILTER)

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
        fragment = render_runs_fragment(listing, filters)

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
        fragment = render_runs_fragment(create_listing([run_of_no_wave], NOTHING_SKIPPED), NO_FILTER)

        # Assert
        self.assertIn('<td><span class="mono">B95</span></td>', fragment)
