import unittest

from brigade.dashboard.render_wave import WavePage, render_wave

STARTED = {"at": "2026-10-19T07:00:00Z", "event": "wave.started", "fields": {"wave": "w4"}}
B27_RUNNING = {"at": "2026-10-19T07:10:00Z", "event": "task.state", "fields": {"task": "B27", "state": "running"}}
B27_RUN = {
    "at": "2026-10-19T07:40:00Z",
    "event": "run.finished",
    "fields": {"task": "B27", "run": "r27", "cost_usd": 3.0},
}
PARKED = {"at": "2026-10-19T08:00:00Z", "event": "wave.parked", "fields": {"wave": "w4", "reason": "quota"}}
MERGE_FAILED = {
    "at": "2026-10-19T08:05:00Z",
    "event": "tick.action_failed",
    "fields": {"action": "merge", "task": "B27", "error": "conflict"},
}
MERGE_FAILED_AGAIN = {**MERGE_FAILED, "at": "2026-10-19T08:10:00Z"}
RESUMED = {"at": "2026-10-19T08:30:00Z", "event": "wave.resumed", "fields": {"wave": "w4", "reason": "quota reset"}}
B27_MERGED = {"at": "2026-10-19T08:40:00Z", "event": "task.state", "fields": {"task": "B27", "state": "merged"}}
B28_RUN = {
    "at": "2026-10-19T08:45:00Z",
    "event": "run.finished",
    "fields": {"task": "B28", "run": "r28", "cost_usd": 1.0},
}
B28_PARKED = {"at": "2026-10-19T09:00:00Z", "event": "task.parked", "fields": {"task": "B28", "reason": "blocked"}}
LEDGER = {
    "view": "wave",
    "wave": "w4",
    "first": "2026-10-19T07:00:00Z",
    "last": "2026-10-19T09:00:00Z",
    "wall_time_ms": 7200000,
    "tasks": ["B27", "B28"],
    "cost_usd": 4.0,
    "by_task": [
        {"task": "B27", "turns": 40, "partial": False, "duration_ms": 1800000, "cost_usd": 3.0},
        {"task": "B28", "turns": 12, "partial": False, "duration_ms": 600000, "cost_usd": 1.0},
    ],
    "halts": [{"halted_at": "2026-10-19T08:00:00Z", "resumed_at": "2026-10-19T08:30:00Z", "duration_ms": 1800000}],
    "halted_ms": 1800000,
    "rounds_by_task": {"B27": 3},
    "turns_by_task": {"B27": 40, "B28": 12},
    "events": [
        STARTED,
        B27_RUNNING,
        B27_RUN,
        PARKED,
        MERGE_FAILED,
        MERGE_FAILED_AGAIN,
        RESUMED,
        B27_MERGED,
        B28_RUN,
        B28_PARKED,
    ],
}
SHOWN = {
    "wave": "w4",
    "project": "oak",
    "milestone": "M4",
    "milestone_report": None,
    "tasks": [
        {"task": "B27", "state": "merged", "pull_request": 235, "run": "r27", "reason": None},
        {"task": "B28", "state": "parked", "pull_request": None, "run": "r28", "reason": "blocked"},
        {"task": "B29", "state": None, "pull_request": None, "run": None, "reason": None},
    ],
    "ledger": LEDGER,
}
ON_GITHUB = {
    "project": {
        "name": "oak",
        "fields": [{"name": "FORGE", "value": "github"}, {"name": "REMOTE", "value": "acme/oak"}],
    }
}
OFF_A_FORGE = {"project": {"name": "oak", "fields": [{"name": "FORGE", "value": "none"}]}}
NO_PROJECT_ANSWER = None


def _tile(label: str, value: str, perimeter: str) -> str:
    return (
        f'<div class="stat-tile"><span class="stat-value">{value}</span>'
        f'<span class="stat-label">{label}</span><span class="stat-perimeter">{perimeter}</span></div>'
    )


class RenderWaveOfAnOpenWaveTest(unittest.TestCase):
    def test_should_open_on_the_sentence_of_a_wave_still_running(self):
        # Act
        fragment = render_wave(WavePage(shown=SHOWN, project=ON_GITHUB))

        # Assert
        self.assertIn(
            '<p class="status-sentence">Wave w4 of oak is running: 1 of 3 tasks merged, 1 parked.</p>', fragment
        )

    def test_should_say_since_when_a_halted_wave_waits_and_offer_to_resume_it(self):
        # Arrange
        halted = {**LEDGER, "halts": [{"halted_at": "2026-10-19T08:00:00Z", "resumed_at": None, "duration_ms": None}]}

        # Act
        fragment = render_wave(WavePage(shown={**SHOWN, "ledger": halted}, project=ON_GITHUB))

        # Assert
        self.assertIn(
            '<p class="status-sentence">Wave w4 of oak is halted since 2026-10-19T08:00:00Z:'
            " 1 of 3 tasks merged, 1 parked.</p></div>"
            ' <button type="button" data-post="/api/waves/w4/resume">resume</button>',
            fragment,
        )

    def test_should_offer_no_resume_to_a_wave_that_resumed(self):
        # Act
        fragment = render_wave(WavePage(shown=SHOWN, project=ON_GITHUB))

        # Assert
        self.assertNotIn("/api/waves/w4/resume", fragment)

    def test_should_show_five_tiles_of_its_tasks_its_times_its_cost_and_its_halts(self):
        # Act
        fragment = render_wave(WavePage(shown=SHOWN, project=ON_GITHUB))

        # Assert
        self.assertIn(
            '<div class="stat-tiles">'
            + _tile("tasks merged", "1 of 3", "1 parked")
            + _tile("wall time", "120m00s", "from 2026-10-19T07:00:00Z to 2026-10-19T09:00:00Z")
            + _tile("run time", "40m00s", "52 turns over 2 runs")
            + _tile("cost", "4.00 USD", "every run records its cost")
            + _tile("time halted", "30m00s", "halts: 1, for quota")
            + "</div>",
            fragment,
        )

    def test_should_mark_the_cost_a_floor_when_a_run_records_none(self):
        # Arrange
        unpriced_run = {"at": "2026-10-19T08:50:00Z", "event": "run.finished", "fields": {"task": "B29", "run": "r29"}}
        ledger = {**LEDGER, "events": [*LEDGER["events"], unpriced_run]}

        # Act
        fragment = render_wave(WavePage(shown={**SHOWN, "ledger": ledger}, project=ON_GITHUB))

        # Assert
        self.assertIn(_tile("cost", "at least 4.00 USD", "a floor: 1 of 3 runs records no cost"), fragment)

    def test_should_cost_nothing_and_say_it_never_halted_before_its_first_run(self):
        # Arrange
        ledger = {
            **LEDGER,
            "cost_usd": None,
            "by_task": [],
            "halts": [],
            "halted_ms": 0,
            "turns_by_task": {},
            "events": [STARTED],
        }

        # Act
        fragment = render_wave(WavePage(shown={**SHOWN, "ledger": ledger}, project=ON_GITHUB))

        # Assert
        self.assertIn(
            _tile("run time", "0m00s", "0 turns over 0 runs")
            + _tile("cost", "0.00 USD", "every run records its cost")
            + _tile("time halted", "0m00s", "never halted"),
            fragment,
        )

    def test_should_link_the_pull_request_of_a_task_on_the_forge_and_flag_it_at_three_rounds(self):
        # Act
        fragment = render_wave(WavePage(shown=SHOWN, project=ON_GITHUB))

        # Assert
        self.assertIn(
            '<tr><td>B27</td><td><span class="pill"><span class="tone tone-done">'
            '<span class="tone-shape" aria-hidden="true">✓</span>merged</span></span></td>'
            '<td><a href="https://github.com/acme/oak/pull/235">#235</a></td>'
            '<td><strong class="flagged">3</strong></td>'
            '<td><a href="#runs/r27">r27</a></td><td>75%</td></tr>',
            fragment,
        )

    def test_should_name_the_pull_request_without_a_link_off_a_forge(self):
        for case, project in [("off a forge", OFF_A_FORGE), ("no answer of project show", NO_PROJECT_ANSWER)]:
            with self.subTest(case=case):
                # Act
                fragment = render_wave(WavePage(shown=SHOWN, project=project))

                # Assert
                self.assertIn("<td>#235</td>", fragment)

    def test_should_keep_the_requeue_button_of_a_parked_task_and_its_share_of_the_cost(self):
        # Act
        fragment = render_wave(WavePage(shown=SHOWN, project=ON_GITHUB))

        # Assert
        self.assertIn(
            '<tr><td>B28</td><td><span class="pill"><span class="tone tone-you">'
            '<span class="tone-shape" aria-hidden="true">▲</span>parked</span></span>'
            ' <button type="button" data-post="/api/waves/w4/tasks/B28/requeue">requeue</button></td>'
            '<td>-</td><td>0</td><td><a href="#runs/r28">r28</a></td><td>25%</td></tr>',
            fragment,
        )

    def test_should_give_no_share_of_a_wave_that_cost_nothing(self):
        # Arrange
        free_tasks = [
            {"task": "B27", "turns": 40, "partial": False, "duration_ms": 1800000, "cost_usd": 0.0},
            {"task": "B28", "turns": 12, "partial": False, "duration_ms": 600000, "cost_usd": 0.0},
        ]
        ledger = {**LEDGER, "cost_usd": 0.0, "by_task": free_tasks}

        # Act
        fragment = render_wave(WavePage(shown={**SHOWN, "ledger": ledger}, project=ON_GITHUB))

        # Assert
        self.assertIn('<td><a href="#runs/r27">r27</a></td><td>-</td></tr>', fragment)

    def test_should_show_a_task_not_started_as_queued_with_no_run_and_no_share(self):
        # Act
        fragment = render_wave(WavePage(shown=SHOWN, project=ON_GITHUB))

        # Assert
        self.assertIn(
            '<tr><td>B29</td><td><span class="pill"><span class="tone tone-faint">'
            '<span class="tone-shape" aria-hidden="true">·</span>queued</span></span></td>'
            "<td>-</td><td>0</td><td>-</td><td>-</td></tr>",
            fragment,
        )

    def test_should_list_the_failed_tick_actions_by_action_with_what_cleared_them(self):
        # Act
        fragment = render_wave(WavePage(shown=SHOWN, project=ON_GITHUB))

        # Assert
        self.assertIn(
            '<ul class="failed-actions"><li>merge, failures: 2, the last at 2026-10-19T08:10:00Z: conflict;'
            " cleared by task.state at 2026-10-19T08:40:00Z</li></ul>",
            fragment,
        )

    def test_should_never_count_the_failure_of_another_action_as_what_cleared_one(self):
        # Arrange
        push_failed = {
            "at": "2026-10-19T08:20:00Z",
            "event": "tick.action_failed",
            "fields": {"action": "push", "task": "B27", "error": "rejected"},
        }
        ledger = {**LEDGER, "events": [STARTED, MERGE_FAILED, push_failed, B27_MERGED]}

        # Act
        fragment = render_wave(WavePage(shown={**SHOWN, "ledger": ledger}, project=ON_GITHUB))

        # Assert
        self.assertIn(
            "<li>merge, failures: 1, the last at 2026-10-19T08:05:00Z: conflict;"
            " cleared by task.state at 2026-10-19T08:40:00Z</li>",
            fragment,
        )

    def test_should_say_when_the_ledger_tells_nothing_cleared_a_failed_action(self):
        # Arrange
        ledger = {**LEDGER, "events": [STARTED, MERGE_FAILED]}

        # Act
        fragment = render_wave(WavePage(shown={**SHOWN, "ledger": ledger}, project=ON_GITHUB))

        # Assert
        self.assertIn(
            "<li>merge, failures: 1, the last at 2026-10-19T08:05:00Z: conflict; not cleared in the ledger</li>",
            fragment,
        )

    def test_should_say_no_tick_action_failed(self):
        # Arrange
        ledger = {**LEDGER, "events": [STARTED]}

        # Act
        fragment = render_wave(WavePage(shown={**SHOWN, "ledger": ledger}, project=ON_GITHUB))

        # Assert
        self.assertIn("<p>No tick action of the wave failed.</p>", fragment)

    def test_should_draw_how_it_went_on_the_timeline(self):
        # Act
        fragment = render_wave(WavePage(shown=SHOWN, project=ON_GITHUB))

        # Assert
        self.assertIn('<section><h2>How it went</h2><svg class="timeline"', fragment)

    def test_should_fold_the_events_of_the_ledger_under_events(self):
        # Arrange
        ledger = {**LEDGER, "events": [STARTED, B28_PARKED]}

        # Act
        fragment = render_wave(WavePage(shown={**SHOWN, "ledger": ledger}, project=ON_GITHUB))

        # Assert
        self.assertIn(
            "<details><summary>Events</summary><ol>"
            "<li>2026-10-19T07:00:00Z wave.started</li>"
            "<li>2026-10-19T09:00:00Z task.parked B28</li>"
            "</ol></details>",
            fragment,
        )

    def test_should_name_its_milestone_without_a_report_before_one_exists(self):
        # Act
        fragment = render_wave(WavePage(shown=SHOWN, project=ON_GITHUB))

        # Assert
        self.assertIn("<h2>Wave w4 of oak</h2><p>Milestone M4.</p>", fragment)

    def test_should_link_the_report_of_its_milestone_once_one_exists(self):
        # Arrange
        shown = {**SHOWN, "milestone_report": "oak_M4"}

        # Act
        fragment = render_wave(WavePage(shown=shown, project=ON_GITHUB))

        # Assert
        self.assertIn('<p>Milestone M4, <a href="#reports/oak_M4">its report</a>.</p>', fragment)

    def test_should_name_no_milestone_for_a_wave_of_tasks_naming_none(self):
        # Arrange
        shown = {**SHOWN, "milestone": None}

        # Act
        fragment = render_wave(WavePage(shown=shown, project=ON_GITHUB))

        # Assert
        self.assertIn("<h2>Wave w4 of oak</h2><p>No milestone.</p>", fragment)

    def test_should_escape_a_task_name_holding_markup(self):
        # Arrange
        markup = "<script>alert(1)</script>"
        shown = {
            **SHOWN,
            "wave": markup,
            "project": markup,
            "milestone": markup,
            "milestone_report": markup,
            "tasks": [{"task": markup, "state": "parked", "pull_request": None, "run": markup, "reason": markup}],
            "ledger": {
                **LEDGER,
                "events": [
                    {"at": markup, "event": markup, "fields": {"task": markup}},
                    {"at": markup, "event": "tick.action_failed", "fields": {"action": markup, "error": markup}},
                ],
            },
        }

        # Act
        fragment = render_wave(WavePage(shown=shown, project=ON_GITHUB))

        # Assert
        self.assertNotIn("<script>", fragment)


class RenderWaveOfAClosedWaveTest(unittest.TestCase):
    def test_should_open_on_the_sentence_of_how_the_wave_ended(self):
        # Arrange
        closed = {"at": "2026-10-19T09:00:00Z", "event": "wave.closed", "fields": {"wave": "w4"}}
        ledger = {**LEDGER, "events": [*LEDGER["events"], closed]}

        # Act
        fragment = render_wave(WavePage(shown={**SHOWN, "ledger": ledger}, project=ON_GITHUB))

        # Assert
        self.assertIn(
            '<p class="status-sentence">Wave w4 of oak closed at 2026-10-19T09:00:00Z:'
            " 1 of 3 tasks merged, 1 parked, in 120m00s for 4.00 USD.</p>",
            fragment,
        )


class RenderWaveHeadTest(unittest.TestCase):
    def test_should_open_on_the_page_head_naming_the_wave_and_its_state(self):
        # Act
        fragment = render_wave(WavePage(shown=SHOWN, project=ON_GITHUB))

        # Assert
        self.assertTrue(fragment.startswith('<header class="page-head"><div><h1>Wave <span class="mono">w4</span> '))
        self.assertIn('<p class="lede">The tasks of one wave, what they cost, and what halted the wave.</p>', fragment)
