import unittest

from brigade.dashboard.render_home import HomeDocuments, render_home

ELM_W1 = {
    "wave": "elm_w1",
    "project": "elm",
    "branch": "integration/elm_w1",
    "last_event": "wave.started",
    "tasks": 3,
    "task_states": {"running": 1, "queued": 2},
    "halt": None,
}
OAK_W2_BLOCKED = {
    "wave": "oak_w2",
    "project": "oak",
    "branch": "integration/oak_w2",
    "last_event": "wave.blocked",
    "tasks": 2,
    "task_states": {"blocked:quota": 2},
    "halt": {"reason": "quota", "resume_at": "2026-10-19T10:00:00Z", "age_s": 600},
}
LIVE_RUN_OF_E1 = {"run": "20261019T080000Z-e1", "slot": "build", "project": "elm", "wave": "elm_w1", "task": "E1"}
STATUS = {
    "schema_version": 1,
    "projects": [{"name": "oak", "paused": False}, {"name": "elm", "paused": True}],
    "waves": [ELM_W1],
    "live_runs": [],
    "awaiting_merge": [],
    "inbox": {"new_signals": 0, "scans": [], "stalls": []},
    "quota": {
        "window_hours": 5,
        "usage": {
            "input_tokens": 10,
            "output_tokens": 20,
            "cache_creation_input_tokens": 30,
            "cache_read_input_tokens": 40,
        },
        "runs_without_usage": 1,
        "blocked_waves": [],
    },
    "last_tick": {"ts": "2026-10-19T08:55:00Z", "duration_ms": 120, "actions_applied": 2},
    "studies": [],
    "orders": [],
}
FRESH_SCHEDULER = {"schema_version": 1, "stale": False, "last_tick": STATUS["last_tick"]}
STALE_SCHEDULER = {**FRESH_SCHEDULER, "stale": True}
QUIET_DAY = {"view": "overview", "events": {"wave.started": 1}}
EMPTY_INBOX = {"schema_version": 1, "signals": [], "families": [], "patterns": [], "answers": []}
NO_TASK_WAITING = {"schema_version": 1, "mode": "dry-run", "tasks_not_launched": []}
HOME = HomeDocuments(
    status=STATUS, scheduler=FRESH_SCHEDULER, ledger=QUIET_DAY, inbox=EMPTY_INBOX, dry_run=NO_TASK_WAITING
)


def create_home(status_change: dict) -> HomeDocuments:
    return HomeDocuments(
        status={**STATUS, **status_change},
        scheduler=FRESH_SCHEDULER,
        ledger=QUIET_DAY,
        inbox=EMPTY_INBOX,
        dry_run=NO_TASK_WAITING,
    )


class RenderHomeSentenceTest(unittest.TestCase):
    def test_should_open_on_the_sentence_saying_whether_brigade_is_stopped_working_or_idle(self):
        # Arrange
        rows = [
            ("a stale tick", STALE_SCHEDULER, {}, "brigade is stopped: the scheduler reports the tick stale."),
            ("a live run", FRESH_SCHEDULER, {"live_runs": [LIVE_RUN_OF_E1]}, "brigade is working: a run is live."),
            ("no open wave", FRESH_SCHEDULER, {"waves": []}, "brigade is idle: no wave is open."),
            (
                "every wave halted",
                FRESH_SCHEDULER,
                {"waves": [OAK_W2_BLOCKED]},
                "brigade is idle: every open wave is halted.",
            ),
            ("waves waiting", FRESH_SCHEDULER, {}, "brigade is idle: the open waves wait for the next tick."),
        ]
        for name, scheduler, status_change, sentence in rows:
            with self.subTest(name):
                home = HomeDocuments(
                    status={**STATUS, **status_change},
                    scheduler=scheduler,
                    ledger=QUIET_DAY,
                    inbox=EMPTY_INBOX,
                    dry_run=NO_TASK_WAITING,
                )

                # Act
                fragment = render_home(home)

                # Assert
                self.assertTrue(fragment.startswith(f'<p class="status-sentence">{sentence}</p>'))


class RenderHomeTilesTest(unittest.TestCase):
    def test_should_show_the_waves_the_runs_what_waits_and_the_quota_as_four_tiles(self):
        # Arrange
        home = create_home(
            {
                "waves": [ELM_W1, OAK_W2_BLOCKED],
                "live_runs": [LIVE_RUN_OF_E1],
                "inbox": {
                    "new_signals": 2,
                    "scans": [{"study": "corpus_lint_oak", "project": "oak", "signals": 2, "oldest_age_s": 7200}],
                    "stalls": [],
                },
                "quota": {
                    **STATUS["quota"],
                    "blocked_waves": [{"wave": "oak_w2", "project": "oak", "resume_at": None}],
                },
            }
        )

        # Act
        fragment = render_home(home)

        # Assert
        self.assertIn(
            '<div class="stat-tiles">'
            '<div class="stat-tile"><span class="stat-value">2</span><span class="stat-label">open waves</span>'
            '<span class="stat-perimeter">1 halted</span></div>'
            '<div class="stat-tile"><span class="stat-value">1</span><span class="stat-label">live runs</span>'
            '<span class="stat-perimeter">now</span></div>'
            '<div class="stat-tile"><span class="stat-value">2</span><span class="stat-label">need you</span>'
            '<span class="stat-perimeter">the oldest 2h</span></div>'
            '<div class="stat-tile"><span class="stat-value">100</span><span class="stat-label">quota tokens</span>'
            '<span class="stat-perimeter">over 5 hours, blocking oak_w2</span></div>'
            "</div>",
            fragment,
        )

    def test_should_take_the_age_of_the_oldest_from_every_thing_waiting_for_the_user(self):
        # Arrange
        rows = [
            ("a halted wave", {"waves": [{**OAK_W2_BLOCKED, "halt": {**OAK_W2_BLOCKED["halt"], "age_s": 172800}}]}),
            (
                "a milestone pull request",
                {
                    "awaiting_merge": [
                        {"project": "oak", "repository": "/srv/oak", "milestone": "M2", "pr": 31, "age_s": 172800}
                    ]
                },
            ),
            (
                "a parked order",
                {
                    "orders": [
                        {
                            "name": "nightly",
                            "recipe": "usage-report",
                            "project": "oak",
                            "run": "20261019T081500Z-n1",
                            "step": "1-gate",
                            "reason": "the gate failed",
                            "age_s": 172800,
                        }
                    ]
                },
            ),
        ]
        scan = {"study": "corpus_lint_oak", "project": "oak", "signals": 1, "oldest_age_s": 900}
        for name, status_change in rows:
            with self.subTest(name):
                home = create_home({**status_change, "inbox": {"new_signals": 1, "scans": [scan], "stalls": []}})

                # Act
                fragment = render_home(home)

                # Assert
                self.assertIn(
                    '<span class="stat-label">need you</span><span class="stat-perimeter">the oldest 2d</span>',
                    fragment,
                )

    def test_should_say_no_age_is_recorded_when_nothing_waiting_carries_one(self):
        # Act
        fragment = render_home(HOME)

        # Assert
        self.assertIn(
            '<span class="stat-label">need you</span><span class="stat-perimeter">no age recorded</span>', fragment
        )

    def test_should_say_the_quota_blocks_no_wave(self):
        # Act
        fragment = render_home(HOME)

        # Assert
        self.assertIn('<span class="stat-perimeter">over 5 hours, blocking no wave</span>', fragment)


class RenderHomeNeedsYouTest(unittest.TestCase):
    def test_should_list_each_thing_waiting_for_the_user_with_the_command_to_copy(self):
        # Arrange
        home = HomeDocuments(
            status={
                **STATUS,
                "waves": [OAK_W2_BLOCKED],
                "awaiting_merge": [
                    {"project": "oak", "repository": "/srv/oak", "milestone": "M2", "pr": 31, "age_s": 60}
                ],
                "inbox": {
                    "new_signals": 1,
                    "scans": [{"study": "corpus_lint_oak", "project": "oak", "signals": 1, "oldest_age_s": 900}],
                    "stalls": [],
                },
                "orders": [
                    {
                        "name": "nightly",
                        "recipe": "usage-report",
                        "project": "oak",
                        "run": "20261019T081500Z-n1",
                        "step": "1-gate",
                        "reason": "the gate failed",
                        "age_s": 60,
                    }
                ],
            },
            scheduler=FRESH_SCHEDULER,
            ledger=QUIET_DAY,
            inbox={**EMPTY_INBOX, "patterns": [{"name": "p1"}, {"name": "p2"}]},
            dry_run=NO_TASK_WAITING,
        )

        # Act
        fragment = render_home(home)

        # Assert
        self.assertIn(
            '<section><h2>Needs you</h2><ul class="needs-you-list">'
            '<li class="needs-you"><span class="needs-you-subject">oak_w2</span>'
            '<span class="needs-you-reason">blocked on quota until 2026-10-19T10:00:00Z</span>'
            '<code class="needs-you-action">brigade wave resume oak_w2</code></li>'
            '<li class="needs-you"><span class="needs-you-subject">2 proposed patterns</span>'
            '<span class="needs-you-reason">the inbox proposes them for ratification</span>'
            '<code class="needs-you-action">brigade inbox list</code></li>'
            '<li class="needs-you"><span class="needs-you-subject">corpus_lint_oak</span>'
            '<span class="needs-you-reason">1 new signals, the oldest 15m</span>'
            '<code class="needs-you-action">brigade inbox list</code></li>'
            '<li class="needs-you"><span class="needs-you-subject">M2 of oak</span>'
            '<span class="needs-you-reason">pull request 31 waits for your merge</span>'
            '<code class="needs-you-action">cd /srv/oak &amp;&amp; gh pr merge 31</code></li>'
            '<li class="needs-you"><span class="needs-you-subject">nightly of oak</span>'
            '<span class="needs-you-reason">parked at 1-gate: the gate failed</span>'
            '<code class="needs-you-action">brigade order resume nightly</code></li>'
            "</ul></section>",
            fragment,
        )

    def test_should_say_a_wave_parked_until_further_notice(self):
        # Arrange
        parked = {**OAK_W2_BLOCKED, "halt": {"reason": "a question", "resume_at": None, "age_s": 60}}
        home = create_home({"waves": [parked]})

        # Act
        fragment = render_home(home)

        # Assert
        self.assertIn('<span class="needs-you-reason">parked on a question</span>', fragment)

    def test_should_say_nothing_needs_the_user(self):
        # Act
        fragment = render_home(HOME)

        # Assert
        self.assertIn(
            '<section><h2>Needs you</h2><div class="empty-state"><p class="empty-why">nothing needs you</p>'
            '<p class="empty-fill">a halted wave, a proposed pattern, a parked scan, a pull request to merge'
            " or a parked order would show here</p></div></section>",
            fragment,
        )

    def test_should_list_apart_as_stale_a_stall_whose_task_merged_since(self):
        # Arrange
        stalls = [
            {"project": "elm", "wave": "elm_w1", "task": "E1", "merged": True},
            {"project": "elm", "wave": "elm_w1", "task": "E2", "merged": False},
        ]
        home = create_home({"inbox": {"new_signals": 2, "scans": [], "stalls": stalls}})

        # Act
        fragment = render_home(home)

        # Assert
        self.assertIn(
            '<h3>Stale</h3><ul class="needs-you-list">'
            '<li class="needs-you"><span class="needs-you-subject">stall of E1 in elm_w1</span>'
            '<span class="needs-you-reason">its task merged since</span>'
            '<code class="needs-you-action">brigade inbox list</code></li></ul>',
            fragment,
        )

    def test_should_render_a_wave_name_holding_markup_escaped(self):
        # Arrange
        wave = {**OAK_W2_BLOCKED, "wave": "<b>w</b>"}
        home = create_home({"waves": [wave]})

        # Act
        fragment = render_home(home)

        # Assert
        self.assertIn('<span class="needs-you-subject">&lt;b&gt;w&lt;/b&gt;</span>', fragment)
        self.assertNotIn("<b>w</b>", fragment)


class RenderHomeTasksWaitingTest(unittest.TestCase):
    def test_should_list_each_task_the_next_tick_does_not_launch_with_its_cause(self):
        # Arrange
        dry_run = {
            **NO_TASK_WAITING,
            "tasks_not_launched": [
                {"project": "elm", "wave": "elm_w1", "task": "E3", "cause": "after E2"},
                {"project": "elm", "wave": "elm_w1", "task": "E4", "cause": "no free build slot: 1 used of SLOTS 1"},
            ],
        }
        home = HomeDocuments(
            status=STATUS, scheduler=FRESH_SCHEDULER, ledger=QUIET_DAY, inbox=EMPTY_INBOX, dry_run=dry_run
        )

        # Act
        fragment = render_home(home)

        # Assert
        self.assertIn(
            "<section><h2>Tasks waiting</h2><ul>"
            '<li><a href="#waves/elm_w1">elm_w1</a> E3: after E2</li>'
            '<li><a href="#waves/elm_w1">elm_w1</a> E4: no free build slot: 1 used of SLOTS 1</li>'
            "</ul></section>",
            fragment,
        )

    def test_should_say_no_task_waits(self):
        # Act
        fragment = render_home(HOME)

        # Assert
        self.assertIn(
            '<section><h2>Tasks waiting</h2><div class="empty-state"><p class="empty-why">no task waits</p>'
            '<p class="empty-fill">a queued or parked task the next tick does not launch would show here'
            " with its cause</p></div></section>",
            fragment,
        )

    def test_should_render_a_cause_holding_markup_escaped(self):
        # Arrange
        dry_run = {
            **NO_TASK_WAITING,
            "tasks_not_launched": [
                {"project": "elm", "wave": "elm_w1", "task": "E3", "cause": "task E3 parked: <b>no</b>"}
            ],
        }
        home = HomeDocuments(
            status=STATUS, scheduler=FRESH_SCHEDULER, ledger=QUIET_DAY, inbox=EMPTY_INBOX, dry_run=dry_run
        )

        # Act
        fragment = render_home(home)

        # Assert
        self.assertIn("E3: task E3 parked: &lt;b&gt;no&lt;/b&gt;</li>", fragment)
        self.assertNotIn("<b>no</b>", fragment)


class RenderHomeAtWorkTest(unittest.TestCase):
    def test_should_list_each_open_wave_with_its_tasks_by_state_and_its_live_runs(self):
        # Arrange
        home = create_home({"live_runs": [LIVE_RUN_OF_E1]})

        # Act
        fragment = render_home(home)

        # Assert
        self.assertIn(
            '<section><h2>At work</h2><ul><li><a href="#waves/elm_w1">elm_w1</a> of elm: running 1, queued 2'
            "<ul><li>20261019T080000Z-e1, build on E1</li></ul></li></ul></section>",
            fragment,
        )

    def test_should_list_under_a_wave_its_own_live_runs_alone(self):
        # Arrange
        home = create_home({"waves": [ELM_W1, OAK_W2_BLOCKED], "live_runs": [LIVE_RUN_OF_E1]})

        # Act
        fragment = render_home(home)

        # Assert
        self.assertIn('<li><a href="#waves/oak_w2">oak_w2</a> of oak: blocked:quota 2</li></ul></section>', fragment)

    def test_should_say_no_wave_is_open(self):
        # Arrange
        home = create_home({"waves": []})

        # Act
        fragment = render_home(home)

        # Assert
        self.assertIn(
            '<section><h2>At work</h2><div class="empty-state"><p class="empty-why">no wave is open</p>'
            '<p class="empty-fill">the tick starts a wave once a milestone holds a ratified task</p></div></section>',
            fragment,
        )

    def test_should_count_the_failed_tick_actions_of_the_last_24_hours(self):
        # Arrange
        home = HomeDocuments(
            status=STATUS,
            scheduler=FRESH_SCHEDULER,
            ledger={"view": "overview", "events": {"tick.action_failed": 3}},
            inbox=EMPTY_INBOX,
            dry_run=NO_TASK_WAITING,
        )

        # Act
        fragment = render_home(home)

        # Assert
        self.assertIn("<section><h2>Last 24 hours</h2><p>3 failed tick actions</p></section>", fragment)

    def test_should_keep_the_pause_and_resume_buttons_of_the_projects(self):
        # Act
        fragment = render_home(HOME)

        # Assert
        self.assertIn(
            "<section><h2>Projects</h2><ul>"
            '<li>oak, active <button type="button" data-post="/api/projects/oak/pause">pause</button></li>'
            '<li>elm, paused <button type="button" data-post="/api/projects/elm/resume">resume</button></li>'
            "</ul></section>",
            fragment,
        )

    def test_should_keep_the_lines_of_the_studies_and_the_parked_orders(self):
        # Arrange
        home = create_home(
            {
                "studies": [
                    {
                        "name": "triage",
                        "status": "active",
                        "every": "24h",
                        "last_run": None,
                        "outcome": None,
                        "due": True,
                    },
                    {
                        "name": "debt",
                        "status": "active",
                        "every": "1d",
                        "last_run": "r1",
                        "outcome": "parked",
                        "due": False,
                    },
                ],
                "orders": [
                    {
                        "name": "nightly",
                        "recipe": "usage-report",
                        "project": "oak",
                        "run": "r2",
                        "step": "1-gate",
                        "reason": "the gate <step> failed",
                        "age_s": 60,
                    }
                ],
            }
        )

        # Act
        fragment = render_home(home)

        # Assert
        self.assertIn(
            "<section><h2>Studies</h2><ul><li>triage, due</li><li>debt, parked</li></ul></section>"
            "<section><h2>Orders</h2><ul><li>nightly of oak, parked at 1-gate: the gate &lt;step&gt; failed</li></ul>"
            "</section>",
            fragment,
        )
