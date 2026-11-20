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


class RenderRunsFragmentTest(unittest.TestCase):
    def test_should_open_on_a_sentence_and_an_explainer_saying_what_a_run_and_a_segment_are(self):
        # Arrange
        listing = create_listing([LIVE_RUN, DEAD_RUN, LIMIT_CUT_RUN, DONE_RUN], NOTHING_SKIPPED)

        # Act
        fragment = render_runs_fragment(listing, NO_FILTER)

        # Assert
        self.assertTrue(
            fragment.startswith(
                '<p class="status-sentence">4 runs listed: 1 live, 2 finished, 1 dead.</p>'
                '<aside class="explainer"><p class="explainer-what">A run is one procedure a role carries out'
                " through a client, for a task of a wave or on its own. It runs in segments: a segment is one"
                " session of the client, and a segment that reaches the cap of its role hands over to the next"
                " through the progress of the run.</p>"
            )
        )

    def test_should_count_the_runs_by_state_and_outcome_and_total_their_run_time_and_their_cost_as_a_floor(self):
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
        fragment = render_runs_fragment(listing, NO_FILTER)

        # Assert
        self.assertIn('<p class="skipped">The list skipped 2 run directories it could not read.</p>', fragment)

    def test_should_show_a_live_run_linked_with_its_task_and_its_wave_its_segments_its_measures_and_its_arguments(self):
        # Arrange
        listing = create_listing([LIVE_RUN], NOTHING_SKIPPED)

        # Act
        fragment = render_runs_fragment(listing, NO_FILTER)

        # Assert
        self.assertIn(
            "<section><h2>Runs</h2><table><thead><tr><th>run</th><th>procedure</th><th>task</th><th>wave</th>"
            "<th>state</th><th>segments</th><th>duration</th><th>cost</th><th>arguments</th><th>start</th></tr></thead>"
            "<tbody>"
            '<tr><td><a href="#runs/20261118T101500Z-a1b2c3">20261118T101500Z-a1b2c3</a></td><td>build-task</td>'
            '<td><a href="#runs?task=B94">B94</a></td><td><a href="#waves/oak_w4">oak_w4</a></td>'
            '<td><span class="pill"><span class="tone tone-work"><span class="tone-shape" aria-hidden="true">●'
            "</span>running</span></span></td>"
            '<td><span class="segment-squares" role="img" aria-label="segments: handed_over, running">'
            '<span class="segment-square tone-faint" title="handed_over"></span>'
            '<span class="segment-square tone-work" title="running"></span></span></td>'
            "<td>at least 12m34s</td><td>at least $1.50</td><td>base=integration/oak task=@TASK.B94</td>"
            "<td>2026-11-18T10:15:00Z</td></tr></tbody></table></section>",
            fragment,
        )

    def test_should_name_a_dead_run_under_a_heading_of_its_own(self):
        # Arrange
        listing = create_listing([LIVE_RUN, DEAD_RUN], NOTHING_SKIPPED)

        # Act
        fragment = render_runs_fragment(listing, NO_FILTER)

        # Assert
        self.assertIn(
            "<section><h2>Dead runs</h2><table><thead><tr><th>run</th><th>procedure</th><th>task</th><th>wave</th>"
            "<th>state</th><th>segments</th><th>duration</th><th>cost</th><th>arguments</th><th>start</th></tr></thead>"
            "<tbody>"
            '<tr><td><a href="#runs/20261118T090000Z-dead01">20261118T090000Z-dead01</a></td>',
            fragment,
        )

    def test_should_name_a_run_a_limit_cut_under_a_heading_of_its_own_with_its_outcome_as_a_pill(self):
        # Arrange
        listing = create_listing([LIVE_RUN, LIMIT_CUT_RUN], NOTHING_SKIPPED)

        # Act
        fragment = render_runs_fragment(listing, NO_FILTER)

        # Assert
        self.assertIn(
            "<section><h2>Runs cut by a limit</h2><table><thead><tr><th>run</th><th>procedure</th><th>task</th>"
            "<th>wave</th><th>state</th><th>segments</th><th>duration</th><th>cost</th><th>arguments</th><th>start</th>"
            "</tr></thead><tbody>"
            '<tr><td><a href="#runs/20261118T080000Z-c0ffee">20261118T080000Z-c0ffee</a></td><td>build-task</td>'
            '<td><a href="#runs?task=B92">B92</a></td><td><a href="#waves/oak_w4">oak_w4</a></td>'
            '<td><span class="pill"><span class="tone tone-limit"><span class="tone-shape" aria-hidden="true">■'
            "</span>turn_limit</span></span></td>",
            fragment,
        )

    def test_should_leave_out_the_heading_of_a_kind_of_run_the_list_holds_none_of(self):
        # Arrange
        listing = create_listing([LIVE_RUN], NOTHING_SKIPPED)

        # Act
        fragment = render_runs_fragment(listing, NO_FILTER)

        # Assert
        self.assertNotIn("<h2>Dead runs</h2>", fragment)
        self.assertNotIn("<h2>Runs cut by a limit</h2>", fragment)

    def test_should_show_a_run_outside_a_wave_and_a_task_with_a_dash(self):
        # Arrange
        listing = create_listing([DONE_RUN], NOTHING_SKIPPED)

        # Act
        fragment = render_runs_fragment(listing, NO_FILTER)

        # Assert
        self.assertIn("<td>vibe</td><td>-</td><td>-</td>", fragment)

    def test_should_offer_the_filters_as_chips_carried_by_the_address_keeping_the_others(self):
        # Arrange
        listing = create_listing([LIVE_RUN, LIMIT_CUT_RUN], NOTHING_SKIPPED)
        filters = RunFilters(state="running", wave="oak_w4", task=None)

        # Act
        fragment = render_runs_fragment(listing, filters)

        # Assert
        self.assertIn(
            '<nav class="chips"><a class="chip" href="#runs?wave=oak_w4">every state</a>'
            '<a class="chip" href="#runs?state=running&amp;wave=oak_w4" aria-current="true">running</a>'
            '<a class="chip" href="#runs?state=finished&amp;wave=oak_w4">finished</a>'
            '<a class="chip" href="#runs?state=dead&amp;wave=oak_w4">dead</a></nav>'
            '<nav class="chips"><a class="chip" href="#runs?state=running">every wave</a>'
            '<a class="chip" href="#runs?state=running&amp;wave=oak_w4" aria-current="true">oak_w4</a></nav>'
            '<nav class="chips"><a class="chip" href="#runs?state=running&amp;wave=oak_w4" aria-current="true">'
            "every task</a>"
            '<a class="chip" href="#runs?state=running&amp;wave=oak_w4&amp;task=B92">B92</a>'
            '<a class="chip" href="#runs?state=running&amp;wave=oak_w4&amp;task=B94">B94</a></nav>',
            fragment,
        )

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

    def test_should_show_the_strip_of_a_run_cut_then_done_and_its_whole_measures(self):
        # Arrange
        listing = create_listing([DONE_RUN], NOTHING_SKIPPED)

        # Act
        fragment = render_runs_fragment(listing, NO_FILTER)

        # Assert
        self.assertIn(
            '<td><span class="segment-squares" role="img" aria-label="segments: wall_limit, done">'
            '<span class="segment-square tone-limit" title="wall_limit"></span>'
            '<span class="segment-square tone-done" title="done"></span></span></td>'
            "<td>35m00s</td><td>$1.75</td><td>-</td>",
            fragment,
        )

    def test_should_render_an_argument_holding_markup_escaped(self):
        # Arrange
        run = {**DONE_RUN, "arguments": {"base": "<script>alert(1)</script>"}}
        listing = create_listing([run], NOTHING_SKIPPED)

        # Act
        fragment = render_runs_fragment(listing, NO_FILTER)

        # Assert
        self.assertIn("<td>base=&lt;script&gt;alert(1)&lt;/script&gt;</td>", fragment)

    def test_should_give_the_cost_by_procedure_marked_a_floor_where_a_run_records_none(self):
        # Arrange
        listing = create_listing([LIVE_RUN, DEAD_RUN, LIMIT_CUT_RUN, DONE_RUN], NOTHING_SKIPPED)

        # Act
        fragment = render_runs_fragment(listing, NO_FILTER)

        # Assert
        self.assertIn(
            "<section><h2>Cost by procedure</h2><table><thead><tr><th>procedure</th><th>runs</th><th>cost</th>"
            "</tr></thead><tbody><tr><td>build-task</td><td>3</td><td>at least $3.00</td></tr>"
            "<tr><td>vibe</td><td>1</td><td>$1.75</td></tr></tbody></table></section>",
            fragment,
        )

    def test_should_leave_out_the_cost_by_procedure_when_no_run_matches(self):
        # Arrange
        no_run = []
        listing = create_listing(no_run, NOTHING_SKIPPED)

        # Act
        fragment = render_runs_fragment(listing, NO_FILTER)

        # Assert
        self.assertNotIn("<h2>Cost by procedure</h2>", fragment)

    def test_should_show_a_dash_for_the_measures_of_a_run_starting_its_first_segment(self):
        # Arrange
        listing = create_listing([STARTING_RUN], NOTHING_SKIPPED)

        # Act
        fragment = render_runs_fragment(listing, NO_FILTER)

        # Assert
        self.assertIn(
            '<td><span class="segment-squares" role="img" aria-label="segments: running">'
            '<span class="segment-square tone-work" title="running"></span></span></td>'
            "<td>-</td><td>-</td><td>-</td>",
            fragment,
        )

    def test_should_total_the_cost_as_a_floor_when_a_run_records_no_cost_yet(self):
        # Arrange
        listing = create_listing([STARTING_RUN], NOTHING_SKIPPED)

        # Act
        fragment = render_runs_fragment(listing, NO_FILTER)

        # Assert
        self.assertIn(
            '<div class="stat-tile"><span class="stat-value">0m00s</span><span class="stat-label">run time</span>'
            '<span class="stat-perimeter">over the segments that ended</span></div>'
            '<div class="stat-tile"><span class="stat-value">at least $0.00</span><span class="stat-label">cost</span>'
            '<span class="stat-perimeter">over the runs listed; runs lacking a cost: 1</span></div>',
            fragment,
        )
