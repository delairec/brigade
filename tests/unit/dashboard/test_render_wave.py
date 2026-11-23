import unittest

from brigade.dashboard.render_wave import WavePage, render_wave

STARTED = {"at": "2026-10-19T07:00:00Z", "event": "wave.started", "fields": {"wave": "w4", "tasks": ["B27", "B28"]}}
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
    "rounds_by_task": {"B27": 0, "B28": 1},
    "pull_requests": [{"task": "B27", "pr": 235, "rounds": 3}],
    "handovers": [],
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
    "halt": None,
}
ON_GITHUB = {
    "project": {
        "name": "oak",
        "fields": [{"name": "FORGE", "value": "github"}, {"name": "REMOTE", "value": "acme/oak"}],
    }
}
OFF_A_FORGE = {"project": {"name": "oak", "fields": [{"name": "FORGE", "value": "none"}]}}
NO_PROJECT_ANSWER = None


RUNS_KEPT = {"schema_version": 1, "runs": [{"run": "r27"}], "skipped": []}
FRESH = '<p class="fresh num" data-fresh>refreshes every 5 s</p>'
RUNNING_PILL = '<span class="pill"><span class="tone tone-work"><span class="tone-shape" aria-hidden="true">●</span>running</span></span>'
PARKED_PILL = '<span class="pill"><span class="tone tone-you"><span class="tone-shape" aria-hidden="true">▲</span>parked</span></span>'
BLOCKED_PILL = '<span class="pill"><span class="tone tone-you"><span class="tone-shape" aria-hidden="true">▲</span>blocked</span></span>'
MERGED_PILL = '<span class="pill"><span class="tone tone-done"><span class="tone-shape" aria-hidden="true">✓</span>merged</span></span>'
QUEUED_PILL = '<span class="pill"><span class="tone tone-faint"><span class="tone-shape" aria-hidden="true">·</span>queued</span></span>'
CLOSED_PILL = '<span class="pill"><span class="tone tone-done"><span class="tone-shape" aria-hidden="true">✓</span>closed</span></span>'
CANCELLED_PILL = '<span class="pill"><span class="tone tone-off"><span class="tone-shape" aria-hidden="true">○</span>cancelled</span></span>'
CLOSED = {"at": "2026-10-19T09:00:00Z", "event": "wave.closed", "fields": {"wave": "w4"}}
OPEN_HALT = [
    {"halted_at": "2026-10-19T08:00:00Z", "resumed_at": None, "duration_ms": None},
]


def _tile(label: str, value: str, perimeter: str) -> str:
    return (
        f'<div class="stat-tile"><span class="stat-value">{value}</span>'
        f'<span class="stat-label">{label}</span><span class="stat-perimeter">{perimeter}</span></div>'
    )


def _cost_bar(percent: str) -> str:
    return (
        f'<svg class="bar" viewBox="0 0 100 8" preserveAspectRatio="none" role="img" aria-label="{percent} percent of'
        f' the cost"><rect class="g-track" width="100" height="8"></rect><rect class="g-ink" width="{percent}"'
        ' height="8"></rect></svg>'
    )


class RenderWaveHeadTest(unittest.TestCase):
    def test_should_name_the_wave_once_under_the_way_back_to_the_waves_of_its_project(self):
        # Act
        fragment = render_wave(WavePage(shown=SHOWN, project=ON_GITHUB))

        # Assert
        self.assertTrue(
            fragment.startswith(
                '<header class="page-head"><div><p class="crumbs"><a href="#waves">Waves</a> / oak / M4</p>'
                f'<h1>Wave <span class="mono">w4</span> {RUNNING_PILL}</h1>'
            )
        )
        self.assertEqual(fragment.count(">w4<"), 1)

    def test_should_link_the_report_of_its_milestone_in_the_way_back_once_one_exists(self):
        # Arrange
        shown = {**SHOWN, "milestone_report": "oak_M4"}

        # Act
        fragment = render_wave(WavePage(shown=shown, project=ON_GITHUB))

        # Assert
        self.assertIn(
            '<p class="crumbs"><a href="#waves">Waves</a> / oak / <a href="#reports/oak_M4">M4</a></p>', fragment
        )

    def test_should_name_no_milestone_in_the_way_back_for_a_wave_of_tasks_naming_none(self):
        # Arrange
        shown = {**SHOWN, "milestone": None}

        # Act
        fragment = render_wave(WavePage(shown=shown, project=ON_GITHUB))

        # Assert
        self.assertIn('<p class="crumbs"><a href="#waves">Waves</a> / oak</p>', fragment)

    def test_should_read_a_running_wave_in_one_sentence_with_the_task_that_cost_the_most(self):
        # Act
        fragment = render_wave(WavePage(shown=SHOWN, project=ON_GITHUB))

        # Assert
        self.assertIn(
            '<p class="lede">1 of 3 tasks merged, 1 parked, running for 2 h.'
            " B27 took 75 % of the cost and 3 review rounds.</p></div>" + FRESH + "</header>",
            fragment,
        )

    def test_should_read_how_a_closed_wave_ended_in_one_sentence(self):
        # Arrange
        ledger = {**LEDGER, "events": [*LEDGER["events"], CLOSED]}
        shown = {
            **SHOWN,
            "tasks": [
                {"task": "B27", "state": "merged", "pull_request": 235, "run": "r27", "reason": None},
                {"task": "B28", "state": "merged", "pull_request": None, "run": "r28", "reason": "blocked"},
            ],
            "ledger": ledger,
        }

        # Act
        fragment = render_wave(WavePage(shown=shown, project=ON_GITHUB))

        # Assert
        self.assertIn(
            f'<h1>Wave <span class="mono">w4</span> {CLOSED_PILL}</h1><p class="lede">All 2 tasks merged in 2 h,'
            " for 4.00 USD. B27 took 75 % of the cost and 3 review rounds.</p>",
            fragment,
        )

    def test_should_read_since_when_a_halted_wave_waits_and_why(self):
        # Arrange
        halted = {**LEDGER, "halts": OPEN_HALT, "events": LEDGER["events"][:6]}

        # Act
        fragment = render_wave(WavePage(shown={**SHOWN, "ledger": halted}, project=ON_GITHUB))

        # Assert
        self.assertIn(
            f'{PARKED_PILL}</h1><p class="lede">1 of 3 tasks merged, 1 parked, halted since 08:00:00Z for quota.'
            " B27 took 75 % of the cost and 3 review rounds.</p>",
            fragment,
        )

    def test_should_name_no_costliest_task_for_a_wave_that_cost_nothing(self):
        # Arrange
        ledger = {**LEDGER, "cost_usd": None, "by_task": [], "events": [STARTED]}

        # Act
        fragment = render_wave(WavePage(shown={**SHOWN, "ledger": ledger}, project=ON_GITHUB))

        # Assert
        self.assertIn('<p class="lede">1 of 3 tasks merged, 1 parked, running for 2 h.</p>', fragment)

    def test_should_show_the_state_the_last_halt_of_the_wave_left_it_in(self):
        # Arrange
        blocked = {"at": "2026-10-19T08:50:00Z", "event": "wave.blocked", "fields": {"wave": "w4", "reason": "quota"}}
        halts = [
            {"halted_at": "2026-10-19T08:00:00Z", "resumed_at": "2026-10-19T08:30:00Z", "duration_ms": 1800000},
            {"halted_at": "2026-10-19T08:50:00Z", "resumed_at": None, "duration_ms": None},
        ]
        ledger = {**LEDGER, "halts": halts, "events": [*LEDGER["events"][:7], blocked]}

        # Act
        fragment = render_wave(WavePage(shown={**SHOWN, "ledger": ledger}, project=ON_GITHUB))

        # Assert
        self.assertIn(f'<h1>Wave <span class="mono">w4</span> {BLOCKED_PILL}</h1>', fragment)

    def test_should_show_a_cancelled_wave_as_cancelled(self):
        # Arrange
        cancelled = {"at": "2026-10-19T09:00:00Z", "event": "wave.cancelled", "fields": {"wave": "w4"}}
        ledger = {**LEDGER, "events": [*LEDGER["events"], cancelled]}

        # Act
        fragment = render_wave(WavePage(shown={**SHOWN, "ledger": ledger}, project=ON_GITHUB))

        # Assert
        self.assertIn(f'<h1>Wave <span class="mono">w4</span> {CANCELLED_PILL}</h1>', fragment)


class RenderWaveTilesTest(unittest.TestCase):
    def test_should_show_five_tiles_of_its_tasks_its_times_its_cost_and_its_halts(self):
        # Act
        fragment = render_wave(WavePage(shown=SHOWN, project=ON_GITHUB))

        # Assert
        self.assertIn(
            '<div class="stat-tiles">'
            + _tile("tasks merged", "1 of 3", "1 parked")
            + _tile("wall time", "2 h", "07:00:00Z → 09:00:00Z")
            + _tile("run time", "40 min", "52 turns · 2 runs")
            + _tile("cost", "4.00 USD", "every run records its cost")
            + _tile("time halted", "30 min", "1 park, quota")
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

    def test_should_count_costless_a_run_whose_earlier_segment_records_no_cost(self):
        # Arrange
        handed_over_segment = {
            "at": "2026-10-19T07:20:00Z",
            "event": "run.finished",
            "fields": {"task": "B27", "run": "r27"},
        }
        ledger = {**LEDGER, "events": [handed_over_segment, *LEDGER["events"]]}

        # Act
        fragment = render_wave(WavePage(shown={**SHOWN, "ledger": ledger}, project=ON_GITHUB))

        # Assert
        self.assertIn(_tile("cost", "at least 4.00 USD", "a floor: 1 of 2 runs records no cost"), fragment)

    def test_should_agree_the_verb_with_several_costless_runs(self):
        # Arrange
        unpriced_runs = [
            {"at": "2026-10-19T08:50:00Z", "event": "run.finished", "fields": {"task": "B29", "run": "r29"}},
            {"at": "2026-10-19T08:55:00Z", "event": "run.finished", "fields": {"task": "B29", "run": "r30"}},
        ]
        ledger = {**LEDGER, "events": [*LEDGER["events"], *unpriced_runs]}

        # Act
        fragment = render_wave(WavePage(shown={**SHOWN, "ledger": ledger}, project=ON_GITHUB))

        # Assert
        self.assertIn(_tile("cost", "at least 4.00 USD", "a floor: 2 of 4 runs record no cost"), fragment)

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
            _tile("run time", "0 s", "0 turns · 0 runs")
            + _tile("cost", "0.00 USD", "every run records its cost")
            + _tile("time halted", "0 s", "never halted"),
            fragment,
        )

    def test_should_count_the_parks_and_the_blocks_of_the_wave_with_their_reasons(self):
        # Arrange
        blocked = {"at": "2026-10-19T08:50:00Z", "event": "wave.blocked", "fields": {"wave": "w4", "reason": "turns"}}
        parked_again = {**PARKED, "at": "2026-10-19T08:55:00Z"}
        ledger = {**LEDGER, "events": [*LEDGER["events"], blocked, parked_again]}

        # Act
        fragment = render_wave(WavePage(shown={**SHOWN, "ledger": ledger}, project=ON_GITHUB))

        # Assert
        self.assertIn(_tile("time halted", "30 min", "2 parks, 1 block, quota, turns"), fragment)


class RenderWaveHaltsTest(unittest.TestCase):
    def test_should_list_each_halt_with_its_reason_its_span_and_how_the_wave_left_it(self):
        # Act
        fragment = render_wave(WavePage(shown=SHOWN, project=ON_GITHUB))

        # Assert
        self.assertIn(
            '<section class="block"><div class="block-head"><h2>Why it waited</h2>'
            "<p>The halts of the wave, and the way out of the current one.</p></div>",
            fragment,
        )
        self.assertIn(
            f'<tr><td>{PARKED_PILL}</td><td class="mono">quota</td><td class="num">08:00:00Z</td>'
            '<td class="num">08:30:00Z</td><td class="num">30 min</td><td>resumed</td></tr>',
            fragment,
        )

    def test_should_offer_to_resume_the_park_the_wave_is_still_in(self):
        # Arrange
        halted = {**LEDGER, "halts": OPEN_HALT, "events": LEDGER["events"][:6]}

        # Act
        fragment = render_wave(WavePage(shown={**SHOWN, "ledger": halted}, project=ON_GITHUB))

        # Assert
        self.assertIn(
            f'<tr><td>{PARKED_PILL}</td><td class="mono">quota</td><td class="num">08:00:00Z</td>'
            '<td class="num">-</td><td class="num">-</td>'
            '<td><button class="btn btn-primary" type="button" data-post="/api/waves/w4/resume">Resume</button></td></tr>',
            fragment,
        )

    def test_should_say_a_wave_blocked_now_resumes_by_itself(self):
        # Arrange
        blocked = {"at": "2026-10-19T08:00:00Z", "event": "wave.blocked", "fields": {"wave": "w4", "reason": "quota"}}
        ledger = {**LEDGER, "halts": OPEN_HALT, "events": [STARTED, B27_RUNNING, B27_RUN, blocked]}

        # Act
        fragment = render_wave(WavePage(shown={**SHOWN, "ledger": ledger}, project=ON_GITHUB))

        # Assert
        self.assertIn('<td class="num">-</td><td class="num">-</td><td>resumes by itself</td></tr>', fragment)
        self.assertNotIn("/api/waves/w4/resume", fragment)

    def test_should_say_the_wave_never_halted(self):
        # Arrange
        ledger = {**LEDGER, "halts": [], "halted_ms": 0, "events": [STARTED]}

        # Act
        fragment = render_wave(WavePage(shown={**SHOWN, "ledger": ledger}, project=ON_GITHUB))

        # Assert
        self.assertIn("<p>The wave never halted.</p></section>", fragment)


class RenderWaveTasksTest(unittest.TestCase):
    def test_should_show_a_merged_task_with_the_rounds_its_merge_recorded_its_turns_its_time_and_its_share(self):
        # Act
        fragment = render_wave(WavePage(shown=SHOWN, project=ON_GITHUB, runs=RUNS_KEPT))

        # Assert
        self.assertIn(
            f'<tr><td><a class="mono" href="#awawa/oak?entity=%40TASK.B27">B27</a></td><td>{MERGED_PILL}</td>'
            '<td><a href="https://github.com/acme/oak/pull/235">#235</a></td>'
            '<td class="num flag">3</td><td class="num">40</td><td class="num">30 min</td>'
            f'<td class="num">{_cost_bar("75")}3.00 USD · 75 %</td>'
            '<td><a class="mono" href="#runs/r27">r27</a></td></tr>',
            fragment,
        )

    def test_should_name_a_run_the_state_no_longer_keeps_without_a_link(self):
        # Act
        fragment = render_wave(WavePage(shown=SHOWN, project=ON_GITHUB, runs=RUNS_KEPT))

        # Assert
        self.assertIn('<td><span class="mono">r28</span></td></tr>', fragment)
        self.assertNotIn('href="#runs/r28"', fragment)

    def test_should_link_no_run_when_the_runs_kept_are_unknown(self):
        # Arrange
        runs_unread = None

        # Act
        fragment = render_wave(WavePage(shown=SHOWN, project=ON_GITHUB, runs=runs_unread))

        # Assert
        self.assertNotIn('href="#runs/', fragment)

    def test_should_shorten_a_run_id_to_its_time_and_its_suffix(self):
        # Arrange
        tasks = [
            {"task": "B27", "state": "merged", "pull_request": 235, "run": "20261118T054529Z-71abc4", "reason": None}
        ]
        runs = {"schema_version": 1, "runs": [{"run": "20261118T054529Z-71abc4"}], "skipped": []}

        # Act
        fragment = render_wave(WavePage(shown={**SHOWN, "tasks": tasks}, project=ON_GITHUB, runs=runs))

        # Assert
        self.assertIn(
            '<td><a class="mono" href="#runs/20261118T054529Z-71abc4" title="20261118T054529Z-71abc4">'
            "…054529Z-71abc4</a></td></tr>",
            fragment,
        )

    def test_should_count_the_rounds_of_a_task_not_merged_yet_as_the_ledger_counts_them(self):
        # Act
        fragment = render_wave(WavePage(shown=SHOWN, project=ON_GITHUB))

        # Assert
        self.assertIn(
            f'<tr><td><a class="mono" href="#awawa/oak?entity=%40TASK.B28">B28</a></td><td>{PARKED_PILL}'
            ' <button type="button" data-post="/api/waves/w4/tasks/B28/requeue">requeue</button></td>'
            '<td>-</td><td class="num">1</td><td class="num">12</td><td class="num">10 min</td>'
            f'<td class="num">{_cost_bar("25")}1.00 USD · 25 %</td><td><span class="mono">r28</span></td></tr>',
            fragment,
        )

    def test_should_name_the_pull_request_without_a_link_off_a_forge(self):
        for case, project in [("off a forge", OFF_A_FORGE), ("no answer of project show", NO_PROJECT_ANSWER)]:
            with self.subTest(case=case):
                # Act
                fragment = render_wave(WavePage(shown=SHOWN, project=project))

                # Assert
                self.assertIn("<td>#235</td>", fragment)

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
        self.assertIn(
            '<td class="num">30 min</td><td class="num">-</td><td><span class="mono">r27</span></td>', fragment
        )

    def test_should_show_a_task_not_started_as_queued_with_no_run_and_no_share(self):
        # Act
        fragment = render_wave(WavePage(shown=SHOWN, project=ON_GITHUB))

        # Assert
        self.assertIn(
            f'<tr><td><a class="mono" href="#awawa/oak?entity=%40TASK.B29">B29</a></td><td>{QUEUED_PILL}</td>'
            '<td>-</td><td class="num">0</td>'
            '<td class="num">0</td><td class="num">-</td><td class="num">-</td><td>-</td></tr>',
            fragment,
        )


class RenderWaveCourseTest(unittest.TestCase):
    def test_should_draw_each_state_of_a_task_as_a_bar_from_its_start_to_the_next_state(self):
        # Act
        fragment = render_wave(WavePage(shown=SHOWN, project=ON_GITHUB))

        # Assert
        self.assertIn(
            '<section class="block"><div class="block-head"><h2>How it went</h2>'
            '<p>Each task from its first run to its merge.</p></div><figure class="panel pad chart"><svg',
            fragment,
        )
        self.assertIn("<title>B27 running from 07:10:00Z to 08:40:00Z, 1 h 30 min</title>", fragment)
        self.assertIn("<title>wave halted from 08:00:00Z to 08:30:00Z</title>", fragment)

    def test_should_set_the_start_and_the_end_of_the_wave_on_the_axis_of_the_chart(self):
        # Act
        fragment = render_wave(WavePage(shown=SHOWN, project=ON_GITHUB))

        # Assert
        self.assertIn(">07:00:00Z</text>", fragment)
        self.assertIn(">09:00:00Z</text>", fragment)

    def test_should_name_each_tone_the_chart_draws_in_its_legend(self):
        # Act
        fragment = render_wave(WavePage(shown=SHOWN, project=ON_GITHUB))

        # Assert
        self.assertIn(
            '</svg><figcaption class="legend"><span class="tone-work">building</span>'
            '<span class="tone-work soft">fixing or rebasing</span>'
            '<span class="tone-review soft">pull request open, waiting</span>'
            '<span class="tone-review">verifying</span><span class="tone-done">merged</span>'
            '<span class="tone-you soft">wave halted</span></figcaption></figure>',
            fragment,
        )

    def test_should_read_the_failed_tick_actions_with_what_cleared_them(self):
        # Act
        fragment = render_wave(WavePage(shown=SHOWN, project=ON_GITHUB))

        # Assert
        self.assertIn(
            '</figure><ul class="panel lines"><li><p><span class="tag">Failed</span>merge failed 2 times,'
            " the last at 08:10:00Z: conflict; cleared by task.state at 08:40:00Z.</p></li></ul>",
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
            "merge failed 1 time, the last at 08:05:00Z: conflict; cleared by task.state at 08:40:00Z.", fragment
        )

    def test_should_say_when_the_ledger_tells_nothing_cleared_a_failed_action(self):
        # Arrange
        ledger = {**LEDGER, "events": [STARTED, MERGE_FAILED]}

        # Act
        fragment = render_wave(WavePage(shown={**SHOWN, "ledger": ledger}, project=ON_GITHUB))

        # Assert
        self.assertIn("merge failed 1 time, the last at 08:05:00Z: conflict; not cleared in the ledger.", fragment)

    def test_should_read_the_handovers_of_a_task(self):
        # Arrange
        handovers = [
            {"task": "B27", "role": "ada", "slot": "build", "segment": 2},
            {"task": "B27", "role": "ada", "slot": "build", "segment": 3},
        ]
        ledger = {**LEDGER, "handovers": handovers, "events": [STARTED]}

        # Act
        fragment = render_wave(WavePage(shown={**SHOWN, "ledger": ledger}, project=ON_GITHUB))

        # Assert
        self.assertIn(
            '<ul class="panel lines"><li><p><span class="tag">Read</span>B27 was handed over 2 times,'
            " its run going on in a fresh segment each time.</p></li>"
            '<li><p><span class="tag">Read</span>No tick action of the wave failed.</p></li></ul>',
            fragment,
        )


class RenderWaveEventsTest(unittest.TestCase):
    def test_should_fold_the_events_under_their_counts_by_kind(self):
        # Act
        fragment = render_wave(WavePage(shown=SHOWN, project=ON_GITHUB))

        # Assert
        self.assertIn(
            '<section class="block"><div class="block-head"><h2>Events</h2>'
            "<p>The 10 events the ledger holds for the wave, in the order recorded.</p></div>"
            '<div class="panel"><details class="fold"><summary>Show the events <span>· 2 task.state'
            " · 2 run.finished · 2 tick.action_failed · 1 wave.started · 3 others</span></summary>"
            '<div class="scroll"><table><thead><tr><th>At</th><th>Event</th><th>Task</th><th>What</th></tr></thead>',
            fragment,
        )

    def test_should_say_what_each_event_tells(self):
        # Act
        fragment = render_wave(WavePage(shown=SHOWN, project=ON_GITHUB))

        # Assert
        self.assertIn(
            '<tr><td class="num">07:00:00Z</td><td class="mono">wave.started</td><td>-</td><td>B27, B28</td></tr>'
            f'<tr><td class="num">07:10:00Z</td><td class="mono">task.state</td><td class="mono">B27</td><td>{RUNNING_PILL}</td></tr>'
            '<tr><td class="num">07:40:00Z</td><td class="mono">run.finished</td><td class="mono">B27</td><td>r27</td></tr>'
            '<tr><td class="num">08:00:00Z</td><td class="mono">wave.parked</td><td>-</td><td>quota</td></tr>'
            '<tr><td class="num">08:05:00Z</td><td class="mono">tick.action_failed</td><td class="mono">B27</td>'
            "<td>merge: conflict</td></tr>",
            fragment,
        )

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
                    {"at": "2026-10-19T07:00:00Z", "event": markup, "fields": {"task": markup, "reason": markup}},
                    {
                        "at": "2026-10-19T07:05:00Z",
                        "event": "tick.action_failed",
                        "fields": {"action": markup, "error": markup},
                    },
                ],
            },
        }

        # Act
        fragment = render_wave(WavePage(shown=shown, project=ON_GITHUB, runs={"runs": [{"run": markup}]}))

        # Assert
        self.assertNotIn("<script>", fragment)


class RenderWaveWordsTest(unittest.TestCase):
    def test_should_read_a_closed_wave_of_one_task_in_the_singular(self):
        # Arrange
        shown = {
            **SHOWN,
            "tasks": [{"task": "B27", "state": "merged", "pull_request": 235, "run": "r27", "reason": None}],
            "ledger": {**LEDGER, "events": [*LEDGER["events"], CLOSED]},
        }

        # Act
        fragment = render_wave(WavePage(shown=shown, project=ON_GITHUB))

        # Assert
        self.assertIn('<p class="lede">Its one task merged in 2 h,', fragment)

    def test_should_read_a_failed_merge_by_the_message_of_the_forge_alone(self):
        # Arrange
        failed = {
            "at": "2026-10-19T08:05:00Z",
            "event": "tick.action_failed",
            "fields": {
                "action": "MergePullRequest",
                "task": "B27",
                "error": "gh pr merge 442 --rebase exited 1: GraphQL: Pull Request has merge conflicts (mergePullRequest)",
            },
        }
        shown = {**SHOWN, "ledger": {**LEDGER, "events": [STARTED, failed]}}

        # Act
        fragment = render_wave(WavePage(shown=shown, project=ON_GITHUB))

        # Assert
        self.assertIn(
            "MergePullRequest failed 1 time, the last at 08:05:00Z: Pull Request has merge conflicts;", fragment
        )


class RenderWaveOfAPlanTest(unittest.TestCase):
    def test_should_fold_under_each_task_its_after_and_its_spec(self):
        # Arrange
        task = {"task": "B28", "state": "merged", "pull_request": None, "run": None, "reason": None}
        planned = {**task, "after": ["B27", "B26"], "spec": ["the list names the state", "the page folds the plan"]}

        # Act
        fragment = render_wave(WavePage(shown={**SHOWN, "tasks": [planned]}, project=ON_GITHUB))

        # Assert
        self.assertIn(
            '<td><a class="mono" href="#awawa/oak?entity=%40TASK.B28">B28</a>'
            '<details class="fold"><summary>Plan <span>· after B27, B26</span></summary>'
            '<ul class="steps"><li>the list names the state</li><li>the page folds the plan</li></ul></details></td>',
            fragment,
        )

    def test_should_say_a_task_of_the_plan_comes_after_nothing(self):
        # Arrange
        task = {"task": "B29", "state": "merged", "pull_request": None, "run": None, "reason": None}

        # Act
        fragment = render_wave(
            WavePage(shown={**SHOWN, "tasks": [{**task, "after": [], "spec": []}]}, project=ON_GITHUB)
        )

        # Assert
        self.assertIn(
            '<details class="fold"><summary>Plan <span>· after nothing</span></summary><ul class="steps"></ul></details>',
            fragment,
        )

    def test_should_escape_the_plan_of_a_task_holding_markup(self):
        # Arrange
        markup = "<script>alert(1)</script>"
        task = {"task": "B28", "state": "merged", "pull_request": None, "run": None, "reason": None}
        shown = {**SHOWN, "tasks": [{**task, "after": [markup], "spec": [markup]}]}

        # Act
        fragment = render_wave(WavePage(shown=shown, project=ON_GITHUB))

        # Assert
        self.assertNotIn("<script>", fragment)
        self.assertIn("<li>&lt;script&gt;alert(1)&lt;/script&gt;</li>", fragment)


class RenderWaveWaitsTest(unittest.TestCase):
    def test_should_name_in_its_row_the_cause_a_queued_task_waits_for(self):
        # Arrange
        waiting = {"task": "B29", "state": "queued", "pull_request": None, "run": None, "reason": "after B28"}

        # Act
        fragment = render_wave(WavePage(shown={**SHOWN, "tasks": [waiting]}, project=ON_GITHUB))

        # Assert
        self.assertIn(
            '<td><span class="pill"><span class="tone tone-faint">'
            '<span class="tone-shape" aria-hidden="true">·</span>queued</span></span>'
            ' <span class="cause">after B28</span></td>',
            fragment,
        )

    def test_should_escape_the_cause_of_a_queued_task_holding_markup(self):
        # Arrange
        waiting = {"task": "B29", "state": "queued", "pull_request": None, "run": None, "reason": "blocked by <b>Q</b>"}

        # Act
        fragment = render_wave(WavePage(shown={**SHOWN, "tasks": [waiting]}, project=ON_GITHUB))

        # Assert
        self.assertIn('<span class="cause">blocked by &lt;b&gt;Q&lt;/b&gt;</span>', fragment)

    def test_should_open_why_it_waited_on_the_halt_of_a_blocked_wave_with_its_reason_and_its_resume_at(self):
        # Arrange
        halt = {"reason": "quota", "resume_at": "2026-10-19T13:00:00Z"}

        # Act
        fragment = render_wave(WavePage(shown={**SHOWN, "halt": halt}, project=ON_GITHUB))

        # Assert
        self.assertIn(
            "<p>The halts of the wave, and the way out of the current one.</p></div>"
            '<div class="callout tone-you"><p>wave w4 blocked until 2026-10-19T13:00:00Z: quota</p></div>',
            fragment,
        )

    def test_should_open_why_it_waited_on_the_halt_of_a_parked_wave_with_the_command_resuming_it(self):
        # Arrange
        halt = {"reason": "forge_account", "resume_at": None}

        # Act
        fragment = render_wave(WavePage(shown={**SHOWN, "halt": halt}, project=ON_GITHUB))

        # Assert
        self.assertIn(
            '<div class="callout tone-you"><p>wave w4 parked: forge_account; it waits for brigade wave resume w4</p></div>',
            fragment,
        )
