import unittest

from brigade.dashboard.render_run_fragment import RunPage, render_run_fragment

RUN_ID = "20261118T101500Z-a1b2c3"
LIVE_RUN = {
    "run": RUN_ID,
    "procedure": "build-task",
    "slot": "build",
    "role": "ada",
    "project": "oak",
    "worktree": "/srv/oak/B94",
    "state": "running",
    "outcome": None,
    "wave": "oak_w4",
    "task": "B94",
    "message": None,
    "started_at": "2026-11-18T10:15:00Z",
}
SEGMENT_OVER_ITS_CAP = {
    "segment": 1,
    "outcome": "handed_over",
    "turns": 80,
    "duration_ms": 754000,
    "started_at": "2026-11-18T10:15:00Z",
    "cost_usd": 1.5,
}
LIVE_SEGMENT = {
    "segment": 2,
    "outcome": None,
    "turns": None,
    "duration_ms": None,
    "started_at": None,
    "cost_usd": None,
}
AWAWA_PROGRESS = {
    "text": "ENTRY e1\n",
    "entities": [
        {
            "type": "ENTRY",
            "name": "e1",
            "fields": [{"name": "DONE", "value": "read the package"}, {"name": "NEXT", "value": "2. write the tests"}],
        },
        {"type": "HANDOVER", "name": "h1", "fields": [{"name": "NEXT", "value": "3. implement"}]},
        {"type": "ENTRY", "name": "e2", "fields": [{"name": "DONE", "value": "wrote the tests"}]},
    ],
}
MARKDOWN_PROGRESS = {"text": "# Progress\n- read <b>it</b>\n", "entities": None}
NO_NOTE = []
BUDGETS = {"schema_version": 1, "roles": {"ada": {"applied": 75}}}
OTHER_RUN_OF_THE_TASK = {
    "run": "20261117T090000Z-0ld000",
    "finished_at": "2026-11-17T10:00:00Z",
    "slot": "build",
    "outcome": "turn_limit",
    "turns": 75,
    "partial": False,
    "duration_ms": 600000,
    "cost_usd": 2.5,
}
TASK_RUNS = {
    "schema_version": 1,
    "view": "task",
    "task": "B94",
    "runs": [OTHER_RUN_OF_THE_TASK, {**OTHER_RUN_OF_THE_TASK, "run": RUN_ID}],
}
WAVE = {"schema_version": 1, "wave": "oak_w4", "ledger": {"cost_usd": 30.0}}


def create_shown(run: dict, segments: list[dict], progress: dict | None, notes: list[dict]) -> dict:
    return {
        "schema_version": 1,
        "run": run,
        "arguments": {"task": "@TASK.B94", "base": "integration/oak"},
        "segments": segments,
        "log": None,
        "notes": notes,
        "progress": progress,
    }


def create_live_page() -> RunPage:
    shown = create_shown(LIVE_RUN, [SEGMENT_OVER_ITS_CAP, LIVE_SEGMENT], AWAWA_PROGRESS, NO_NOTE)
    return RunPage(shown=shown, budgets=BUDGETS, task_runs=TASK_RUNS, wave=WAVE)


class RenderRunFragmentTest(unittest.TestCase):
    def test_should_open_on_where_a_live_run_stands_and_the_last_next_entry_of_its_progress(self):
        # Act
        fragment = render_run_fragment(create_live_page())

        # Assert
        self.assertTrue(
            fragment.startswith(
                f"<h2>Run {RUN_ID}</h2>"
                '<p class="status-sentence">build-task by ada is running, in its segment 2.</p>'
                '<div class="callout tone-work"><p>Left for its next segment: 3. implement</p></div>'
            )
        )

    def test_should_show_five_tiles_outcome_segments_turns_run_time_and_cost(self):
        # Act
        fragment = render_run_fragment(create_live_page())

        # Assert
        self.assertIn(
            '<div class="stat-tiles">'
            '<div class="stat-tile"><span class="stat-value">running</span><span class="stat-label">outcome</span>'
            '<span class="stat-perimeter">the run left no message</span></div>'
            '<div class="stat-tile"><span class="stat-value">2</span><span class="stat-label">segments</span>'
            '<span class="stat-perimeter">handovers: 1</span></div>'
            '<div class="stat-tile"><span class="stat-value">80</span><span class="stat-label">turns</span>'
            '<span class="stat-perimeter">against the cap of 75 turns a segment of ada</span></div>'
            '<div class="stat-tile"><span class="stat-value">12m34s</span><span class="stat-label">run time</span>'
            '<span class="stat-perimeter">over the segments that ended</span></div>'
            '<div class="stat-tile"><span class="stat-value">at least $1.50</span>'
            '<span class="stat-label">cost</span>'
            '<span class="stat-perimeter">5% of the $30.00 of wave oak_w4</span></div>'
            "</div>",
            fragment,
        )

    def test_should_show_each_segment_with_its_turns_as_a_bar_against_the_cap_and_one_over_it_said(self):
        # Act
        fragment = render_run_fragment(create_live_page())

        # Assert
        self.assertIn(
            "<section><h3>Segments</h3><table><thead><tr><th>segment</th><th>outcome</th><th>turns</th>"
            "<th>start</th><th>duration</th><th>cost</th></tr></thead><tbody>"
            '<tr><td>1</td><td><span class="pill"><span class="tone tone-faint"><span class="tone-shape"'
            ' aria-hidden="true">·</span>handed_over</span></span></td>'
            '<td><svg class="bar" viewBox="0 0 100 8" role="img" aria-label="80 of 75 turns">'
            '<rect class="bar-track" width="100" height="8"></rect>'
            '<rect class="bar-fill tone-faint" width="100" height="8"></rect></svg>80/75, over its cap</td>'
            "<td>2026-11-18T10:15:00Z</td><td>12m34s</td><td>$1.50</td></tr>"
            '<tr><td>2</td><td><span class="pill"><span class="tone tone-work"><span class="tone-shape"'
            ' aria-hidden="true">●</span>running</span></span></td><td>-</td><td>-</td><td>-</td><td>-</td></tr>'
            "</tbody></table></section>",
            fragment,
        )

    def test_should_show_a_segment_under_its_cap_without_the_mention(self):
        # Arrange
        segment = {**SEGMENT_OVER_ITS_CAP, "turns": 60}
        shown = create_shown(LIVE_RUN, [segment], AWAWA_PROGRESS, NO_NOTE)

        # Act
        fragment = render_run_fragment(RunPage(shown=shown, budgets=BUDGETS, task_runs=TASK_RUNS, wave=WAVE))

        # Assert
        self.assertIn("</svg>60/75</td>", fragment)

    def test_should_show_the_turns_alone_when_no_cap_is_recorded_for_the_role(self):
        # Arrange
        shown = create_shown(LIVE_RUN, [SEGMENT_OVER_ITS_CAP], AWAWA_PROGRESS, NO_NOTE)
        no_budgets = None

        # Act
        fragment = render_run_fragment(RunPage(shown=shown, budgets=no_budgets, task_runs=TASK_RUNS, wave=WAVE))

        # Assert
        self.assertIn('<span class="stat-perimeter">no cap recorded for ada</span>', fragment)
        self.assertIn("</span></td><td>80</td>", fragment)

    def test_should_say_where_a_dead_run_stands(self):
        # Arrange
        shown = create_shown({**LIVE_RUN, "state": "dead"}, [SEGMENT_OVER_ITS_CAP], AWAWA_PROGRESS, NO_NOTE)

        # Act
        fragment = render_run_fragment(RunPage(shown=shown, budgets=BUDGETS, task_runs=TASK_RUNS, wave=WAVE))

        # Assert
        self.assertIn(
            '<p class="status-sentence">build-task by ada died in its segment 1, without a result.</p>', fragment
        )

    def test_should_say_a_live_run_with_no_segment_yet_is_starting_its_first(self):
        # Arrange
        no_segment = []
        shown = create_shown(LIVE_RUN, no_segment, None, NO_NOTE)

        # Act
        fragment = render_run_fragment(RunPage(shown=shown, budgets=BUDGETS, task_runs=TASK_RUNS, wave=WAVE))

        # Assert
        self.assertIn(
            '<p class="status-sentence">build-task by ada is running, before its first segment started.</p>', fragment
        )

    def test_should_say_a_dead_run_with_no_segment_died_before_its_first(self):
        # Arrange
        no_segment = []
        shown = create_shown({**LIVE_RUN, "state": "dead"}, no_segment, None, NO_NOTE)

        # Act
        fragment = render_run_fragment(RunPage(shown=shown, budgets=BUDGETS, task_runs=TASK_RUNS, wave=WAVE))

        # Assert
        self.assertIn(
            '<p class="status-sentence">build-task by ada died before its first segment started, without a result.</p>',
            fragment,
        )

    def test_should_say_where_a_run_a_limit_cut_stands_with_its_message(self):
        # Arrange
        run = {**LIVE_RUN, "state": "finished", "outcome": "turn_limit", "message": "cut at 75 turns"}
        segment = {**SEGMENT_OVER_ITS_CAP, "outcome": "turn_limit", "cost_usd": 2.0}
        shown = create_shown(run, [segment], AWAWA_PROGRESS, NO_NOTE)

        # Act
        fragment = render_run_fragment(RunPage(shown=shown, budgets=BUDGETS, task_runs=TASK_RUNS, wave=WAVE))

        # Assert
        self.assertIn('<p class="status-sentence">build-task by ada finished on turn_limit.</p>', fragment)
        self.assertIn(
            '<div class="stat-tile"><span class="stat-value">turn_limit</span><span class="stat-label">outcome</span>'
            '<span class="stat-perimeter">cut at 75 turns</span></div>',
            fragment,
        )
        self.assertIn('<span class="stat-value">$2.00</span>', fragment)

    def test_should_say_there_is_no_cost_to_share_outside_a_wave(self):
        # Arrange
        shown = create_shown({**LIVE_RUN, "wave": None}, [SEGMENT_OVER_ITS_CAP], AWAWA_PROGRESS, NO_NOTE)
        no_wave = None

        # Act
        fragment = render_run_fragment(RunPage(shown=shown, budgets=BUDGETS, task_runs=TASK_RUNS, wave=no_wave))

        # Assert
        self.assertIn('<span class="stat-perimeter">no cost of a wave to share</span>', fragment)

    def test_should_show_the_progress_cut_by_segment(self):
        # Act
        fragment = render_run_fragment(create_live_page())

        # Assert
        self.assertIn(
            "<section><h3>Progress</h3>"
            "<h4>Segment 1</h4><dl><dt>ENTRY e1</dt><dd>DONE: read the package</dd><dd>NEXT: 2. write the tests</dd>"
            "<dt>HANDOVER h1</dt><dd>NEXT: 3. implement</dd></dl>"
            "<h4>Segment 2</h4><dl><dt>ENTRY e2</dt><dd>DONE: wrote the tests</dd></dl></section>",
            fragment,
        )

    def test_should_show_a_markdown_progress_as_text_without_a_next_entry(self):
        # Arrange
        shown = create_shown(LIVE_RUN, [SEGMENT_OVER_ITS_CAP], MARKDOWN_PROGRESS, NO_NOTE)

        # Act
        fragment = render_run_fragment(RunPage(shown=shown, budgets=BUDGETS, task_runs=TASK_RUNS, wave=WAVE))

        # Assert
        self.assertIn(
            "<section><h3>Progress</h3><pre># Progress\n- read &lt;b&gt;it&lt;/b&gt;\n</pre></section>", fragment
        )
        self.assertNotIn("callout", fragment)

    def test_should_show_no_progress_section_for_a_run_that_wrote_none(self):
        # Arrange
        no_progress = None
        shown = create_shown(LIVE_RUN, [SEGMENT_OVER_ITS_CAP], no_progress, NO_NOTE)

        # Act
        fragment = render_run_fragment(RunPage(shown=shown, budgets=BUDGETS, task_runs=TASK_RUNS, wave=WAVE))

        # Assert
        self.assertNotIn("<h3>Progress</h3>", fragment)

    def test_should_say_no_note_was_handed_to_the_run(self):
        # Act
        fragment = render_run_fragment(create_live_page())

        # Assert
        self.assertIn(
            '<section><h3>Notes</h3><div class="empty-state"><p class="empty-why">No note was handed to this run.</p>'
            '<p class="empty-fill">brigade run note hands a note to the next segment of a run.</p></div></section>',
            fragment,
        )

    def test_should_list_the_notes_handed_to_the_run_and_the_segment_that_carried_each(self):
        # Arrange
        notes = [
            {"at": "2026-11-18T10:30:00Z", "text": "rebase first", "segment": 2},
            {"at": "2026-11-18T10:40:00Z", "text": "then push", "segment": None},
        ]
        shown = create_shown(LIVE_RUN, [SEGMENT_OVER_ITS_CAP], AWAWA_PROGRESS, notes)

        # Act
        fragment = render_run_fragment(RunPage(shown=shown, budgets=BUDGETS, task_runs=TASK_RUNS, wave=WAVE))

        # Assert
        self.assertIn(
            "<section><h3>Notes</h3><table><thead><tr><th>noted</th><th>carried by</th><th>note</th></tr></thead>"
            "<tbody><tr><td>2026-11-18T10:30:00Z</td><td>segment 2</td><td>rebase first</td></tr>"
            "<tr><td>2026-11-18T10:40:00Z</td><td>pending</td><td>then push</td></tr></tbody></table></section>",
            fragment,
        )

    def test_should_follow_with_the_other_runs_of_its_task(self):
        # Act
        fragment = render_run_fragment(create_live_page())

        # Assert
        self.assertIn(
            "<section><h3>Other runs of task B94</h3><table><thead><tr><th>run</th><th>finished</th><th>slot</th>"
            "<th>outcome</th><th>turns</th><th>duration</th><th>cost</th></tr></thead><tbody>"
            '<tr><td><a href="#runs/20261117T090000Z-0ld000">20261117T090000Z-0ld000</a></td>'
            '<td>2026-11-17T10:00:00Z</td><td>build</td><td><span class="pill"><span class="tone tone-limit">'
            '<span class="tone-shape" aria-hidden="true">■</span>turn_limit</span></span></td>'
            "<td>75</td><td>10m00s</td><td>$2.50</td></tr></tbody></table></section>",
            fragment,
        )

    def test_should_say_no_other_run_of_its_task_finished_when_the_ledger_names_none(self):
        # Arrange
        shown = create_shown(LIVE_RUN, [SEGMENT_OVER_ITS_CAP], AWAWA_PROGRESS, NO_NOTE)
        no_task_runs = None

        # Act
        fragment = render_run_fragment(RunPage(shown=shown, budgets=BUDGETS, task_runs=no_task_runs, wave=WAVE))

        # Assert
        self.assertIn(
            '<section><h3>Other runs of task B94</h3><div class="empty-state">'
            '<p class="empty-why">No other run of task B94 has finished.</p>'
            '<p class="empty-fill">A run of the task appears here once it finishes.</p></div></section>',
            fragment,
        )

    def test_should_follow_with_no_other_runs_for_a_run_outside_a_task(self):
        # Arrange
        shown = create_shown({**LIVE_RUN, "task": None}, [SEGMENT_OVER_ITS_CAP], AWAWA_PROGRESS, NO_NOTE)

        # Act
        fragment = render_run_fragment(RunPage(shown=shown, budgets=BUDGETS, task_runs=None, wave=WAVE))

        # Assert
        self.assertNotIn("Other runs", fragment)

    def test_should_render_an_argument_holding_markup_escaped(self):
        # Arrange
        shown = {**create_shown(LIVE_RUN, [SEGMENT_OVER_ITS_CAP], AWAWA_PROGRESS, NO_NOTE)}
        shown["arguments"] = {"base": "<script>alert(1)</script>"}

        # Act
        fragment = render_run_fragment(RunPage(shown=shown, budgets=BUDGETS, task_runs=TASK_RUNS, wave=WAVE))

        # Assert
        self.assertIn(
            "<section><h3>Arguments</h3><dl><dt>base</dt><dd>&lt;script&gt;alert(1)&lt;/script&gt;</dd></dl></section>",
            fragment,
        )
