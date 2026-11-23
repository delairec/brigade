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
    "projects": [
        {"name": "oak", "paused": False, "forge": "github", "remote": "git@github.com:o/oak.git", "corpus": True},
        {"name": "elm", "paused": True, "forge": "none", "remote": None, "corpus": False},
    ],
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
    "last_closed_wave": None,
    "last_milestone_reported": None,
}
OAK_W1_CLOSED = {"wave": "oak_w1", "project": "oak", "closed_at": "2026-10-19T05:50:00Z", "tasks": 4, "merged": 4}
M13_REACHED = {
    "project": "oak",
    "milestone": "M13",
    "report": "oak_M13",
    "reported_at": "2026-10-19T05:00:00Z",
    "reached_main_at": "2026-10-19T06:00:00Z",
}
FRESH_SCHEDULER = {"schema_version": 1, "stale": False, "last_tick": STATUS["last_tick"]}
STALE_SCHEDULER = {**FRESH_SCHEDULER, "stale": True}
NO_SEGMENT = {"outcomes": {}, "error_classes": {}}
QUIET_DAY = {
    "view": "overview",
    "events": {"wave.started": 1},
    "segments": NO_SEGMENT,
    "waves_started": {},
    "since": "2026-10-18T09:00:00Z",
}
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
            (
                "a stale tick",
                STALE_SCHEDULER,
                {},
                "failed",
                "brigade is stopped: the scheduler reports the tick stale.",
            ),
            (
                "a live run",
                FRESH_SCHEDULER,
                {"live_runs": [LIVE_RUN_OF_E1]},
                "work",
                "brigade is working: a run is live.",
            ),
            ("no open wave", FRESH_SCHEDULER, {"waves": []}, "faint", "brigade is idle: no wave is open."),
            (
                "every wave halted",
                FRESH_SCHEDULER,
                {"waves": [OAK_W2_BLOCKED]},
                "you",
                "brigade is idle: every open wave is halted.",
            ),
            ("waves waiting", FRESH_SCHEDULER, {}, "faint", "brigade is idle: the open waves wait for the next tick."),
        ]
        for name, scheduler, status_change, tone, sentence in rows:
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
                self.assertTrue(
                    fragment.startswith(
                        '<header class="page-head"><div><h1>Home</h1><p class="lede">Whether brigade is working, what waits for you, and what it will do next.</p></div><p class="fresh num" data-fresh>refreshes every 5 s</p></header>'
                        f'<div class="verdict tone-{tone}"><p class="status-sentence">{sentence}</p>'
                    )
                )

    def test_should_tone_an_idle_verdict_amber_whenever_something_waits_for_the_user(self):
        # Arrange
        home = HomeDocuments(
            status={**STATUS, "waves": []},
            scheduler=FRESH_SCHEDULER,
            ledger=QUIET_DAY,
            inbox={**EMPTY_INBOX, "patterns": [{"name": "p1", "signals": []}]},
            dry_run=NO_TASK_WAITING,
        )

        # Act
        fragment = render_home(home)

        # Assert
        self.assertIn(
            '<div class="verdict tone-you"><p class="status-sentence">brigade is idle: no wave is open.</p>', fragment
        )

    def test_should_explain_the_sentence_by_what_waits_for_the_user(self):
        # Arrange
        rows = [
            (
                "nothing waits",
                {},
                "<p>Nothing waits for you. The tick is healthy: it last ran 2026-10-19 08:55Z.</p></div>",
            ),
            (
                "a halted wave",
                {"waves": [OAK_W2_BLOCKED]},
                "<p>Waiting for you: 1, listed under Needs you. The tick is healthy: it last ran 2026-10-19 08:55Z.</p></div>",
            ),
        ]
        for name, status_change, explanation in rows:
            with self.subTest(name):
                # Act
                fragment = render_home(create_home(status_change))

                # Assert
                self.assertIn(explanation, fragment)

    def test_should_recall_the_last_wave_closed_and_the_last_milestone_reported(self):
        # Arrange
        rows = [
            (
                "a wave of tasks all merged and a milestone that reached main",
                {"last_closed_wave": OAK_W1_CLOSED, "last_milestone_reported": M13_REACHED},
                (
                    '<p>Nothing waits for you. The last wave, <a class="mono" href="#waves/oak_w1">oak_w1</a>,'
                    " closed 2026-10-19 05:50Z with every task merged,"
                    " and milestone M13 of oak reached main. The tick is healthy: it last ran 2026-10-19 08:55Z.</p>"
                ),
            ),
            (
                "a wave leaving tasks unmerged",
                {"last_closed_wave": OAK_W1_CLOSED | {"merged": 3}},
                (
                    '<p>Nothing waits for you. The last wave, <a class="mono" href="#waves/oak_w1">oak_w1</a>,'
                    " closed 2026-10-19 05:50Z with 3 of its 4 tasks"
                    " merged. The tick is healthy: it last ran 2026-10-19 08:55Z.</p>"
                ),
            ),
            (
                "a milestone whose pull request is not merged",
                {"last_milestone_reported": M13_REACHED | {"reached_main_at": None}},
                (
                    "<p>Nothing waits for you. Milestone M13 of oak was reported."
                    " The tick is healthy: it last ran 2026-10-19 08:55Z.</p>"
                ),
            ),
        ]
        for name, status_change, explanation in rows:
            with self.subTest(name):
                # Act
                fragment = render_home(create_home(status_change))

                # Assert
                self.assertIn(explanation, fragment)


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

    def test_should_write_the_tokens_of_the_quota_with_thousands_separators(self):
        # Arrange
        heavy_usage = {"input_tokens": 242, "output_tokens": 54126, "cache_read_input_tokens": 9935680}
        home = create_home({"quota": {**STATUS["quota"], "usage": heavy_usage}})

        # Act
        fragment = render_home(home)

        # Assert
        self.assertIn('<span class="stat-value">9,990,048</span><span class="stat-label">quota tokens</span>', fragment)

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
            inbox={
                **EMPTY_INBOX,
                "signals": [{"id": "s1"}, {"id": "s2"}],
                "patterns": [{"name": "p1", "signals": ["s1"]}, {"name": "p2", "signals": ["s1", "s9"]}],
            },
            dry_run=NO_TASK_WAITING,
        )

        # Act
        fragment = render_home(home)

        # Assert
        self.assertIn(
            '<section class="block"><div class="block-head"><h2>Needs you</h2><p>What stays stopped until you act, most blocking first.</p></div><ul class="needs-you-list">'
            '<li class="needs-you tone-you"><span class="mark">II</span>'
            "<div><h3>Wave oak_w2 is halted</h3><p>blocked on quota until 2026-10-19T10:00:00Z</p></div>"
            '<div class="act"><code class="cmd">brigade wave resume oak_w2</code></div></li>'
            '<li class="needs-you tone-you"><span class="mark">?</span>'
            "<div><h3>2 proposed patterns wait for a decision</h3>"
            "<p>they cover 1 of the 2 new signals</p></div>"
            '<div class="act"><a class="btn btn-primary" href="#inbox">Decide in the inbox</a></div></li>'
            '<li class="needs-you tone-you"><span class="mark">II</span>'
            "<div><h3>1 scans are parked: corpus_lint_oak</h3><p>1 new signals, the oldest 15m</p></div>"
            '<div class="act"><code class="cmd">brigade study run corpus_lint_oak</code></div></li>'
            '<li class="needs-you tone-you"><span class="mark">?</span>'
            "<div><h3>Milestone M2 of oak waits for your merge</h3><p>pull request 31 is open</p></div>"
            '<div class="act"><code class="cmd">cd /srv/oak &amp;&amp; gh pr merge 31</code></div></li>'
            '<li class="needs-you tone-you"><span class="mark">II</span>'
            "<div><h3>Order nightly of oak is parked</h3><p>parked at 1-gate: the gate failed</p></div>"
            '<div class="act"><code class="cmd">brigade order resume nightly</code></div></li>'
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
        self.assertIn("<p>parked on a question</p>", fragment)

    def test_should_say_nothing_needs_the_user(self):
        # Act
        fragment = render_home(HOME)

        # Assert
        self.assertIn(
            '<section class="block"><div class="block-head"><h2>Needs you</h2><p>What stays stopped until you act, most blocking first.</p></div><div class="empty-state"><p class="empty-why">nothing needs you</p>'
            '<p class="empty-fill">a halted wave, a proposed pattern, a parked scan, a pull request to merge'
            " or a parked order would show here</p></div></section>",
            fragment,
        )

    def test_should_group_the_stalls_whose_task_merged_since_in_one_last_row(self):
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
            '<li class="needs-you tone-faint"><span class="mark">~</span>'
            "<div><h3>1 stall signals name tasks that merged since</h3><p>E1 of elm_w1</p></div>"
            '<div class="act"><a class="btn" href="#inbox">Review</a></div></li></ul></section>',
            fragment,
        )

    def test_should_render_a_wave_name_holding_markup_escaped(self):
        # Arrange
        wave = {**OAK_W2_BLOCKED, "wave": "<b>w</b>"}
        home = create_home({"waves": [wave]})

        # Act
        fragment = render_home(home)

        # Assert
        self.assertIn("<h3>Wave &lt;b&gt;w&lt;/b&gt; is halted</h3>", fragment)
        self.assertNotIn("<b>w</b>", fragment)


class RenderHomeTasksWaitingTest(unittest.TestCase):
    def test_should_say_beside_its_open_wave_why_each_task_the_next_tick_does_not_launch_waits(self):
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
            "<td>E3: after E2<br>E4: no free build slot: 1 used of SLOTS 1</td></tr></tbody></table></section>",
            fragment,
        )

    def test_should_say_nothing_holds_a_wave_whose_tasks_all_launch(self):
        # Act
        fragment = render_home(HOME)

        # Assert
        self.assertIn("<td>\u2013</td><td>\u2013</td></tr></tbody></table></section>", fragment)

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
        self.assertIn("<td>E3: task E3 parked: &lt;b&gt;no&lt;/b&gt;</td>", fragment)
        self.assertNotIn("<b>no</b>", fragment)


class RenderHomeAtWorkTest(unittest.TestCase):
    def test_should_lay_each_open_wave_in_a_row_with_its_state_its_tasks_merged_and_its_live_run(self):
        # Arrange
        home = create_home({"live_runs": [LIVE_RUN_OF_E1]})

        # Act
        fragment = render_home(home)

        # Assert
        self.assertIn(
            '<section class="block"><div class="block-head"><h2>At work</h2><p>Open waves and live runs.</p></div><table><thead><tr><th>wave</th><th>state</th><th>tasks</th><th>live run</th><th>why nothing runs</th>'
            '</tr></thead><tbody><tr><td><a href="#waves/elm_w1">elm_w1</a><br><span class="muted">elm</span></td>'
            '<td><span class="pill"><span class="tone tone-work"><span class="tone-shape" aria-hidden="true">●</span>running</span></span></td><td><svg class="segment-strip"',
            fragment,
        )
        self.assertIn(
            '</svg> <span class="muted num">0 of 3 merged</span></td>'
            '<td><a href="#runs/20261019T080000Z-e1">20261019T080000Z-e1</a><br><span class="muted">build · E1</span>'
            "</td><td>\u2013</td></tr></tbody></table></section>",
            fragment,
        )

    def test_should_list_under_a_wave_its_own_live_runs_alone(self):
        # Arrange
        home = create_home({"waves": [ELM_W1, OAK_W2_BLOCKED], "live_runs": [LIVE_RUN_OF_E1]})

        # Act
        fragment = render_home(home)

        # Assert
        self.assertIn(
            '<span class="muted num">0 of 2 merged</span></td><td>\u2013</td><td>\u2013</td></tr></tbody></table></section>',
            fragment,
        )

    def test_should_say_no_wave_is_open(self):
        # Arrange
        home = create_home({"waves": []})

        # Act
        fragment = render_home(home)

        # Assert
        self.assertIn(
            '<section class="block"><div class="block-head"><h2>At work</h2><p>Open waves and live runs.</p></div><div class="empty-state"><p class="empty-why">no wave is open</p>'
            '<p class="empty-fill">the tick starts a wave once a milestone holds a ratified task</p></div></section>',
            fragment,
        )

    def test_should_count_what_the_last_24_hours_did_one_line_per_kind_of_work(self):
        # Arrange
        home = HomeDocuments(
            status=STATUS,
            scheduler=FRESH_SCHEDULER,
            ledger={**QUIET_DAY, "events": {"tick.action_failed": 3}},
            inbox=EMPTY_INBOX,
            dry_run=NO_TASK_WAITING,
        )

        # Act
        fragment = render_home(home)

        # Assert
        self.assertIn(
            '<section class="block"><div class="block-head"><h2>Last 24 hours</h2><p>Since 2026-10-18 09:00Z.</p></div><ul class="lines">'
            '<li><a href="#waves">0 waves started</a>, <a href="#waves">0 closed</a></li>'
            '<li><a href="#waves">0 pull requests opened</a>, <a href="#waves">0 merged</a></li>'
            '<li><a href="#reports">0 milestones reported</a></li>'
            '<li><a href="#runs">0 run segments finished</a></li>'
            '<li><a href="#ledger">3 failed tick actions</a></li></ul></section>',
            fragment,
        )

    def test_should_lay_the_projects_in_a_table_with_their_state_their_open_waves_and_their_button(self):
        # Act
        fragment = render_home(HOME)

        # Assert
        self.assertIn(
            '<section class="block"><div class="block-head"><h2>Projects</h2></div><table><thead><tr><th>project</th><th>state</th><th>forge</th>'
            "<th>open waves</th><th>corpus</th><th></th></tr></thead><tbody>"
            '<tr><td>oak</td><td><span class="pill"><span class="tone tone-faint"><span class="tone-shape" aria-hidden="true">·</span>active</span></span></td>'
            '<td>github · <span class="mono">git@github.com:o/oak.git</span></td><td>0</td>'
            '<td><a href="#awawa/oak">corpus</a></td>'
            '<td> <button type="button" data-post="/api/projects/oak/pause">pause</button></td></tr>'
            '<tr><td>elm</td><td><span class="pill"><span class="tone tone-you"><span class="tone-shape" aria-hidden="true">▲</span>paused</span></span></td>'
            "<td>none</td><td>1</td><td>\u2013</td>"
            '<td> <button type="button" data-post="/api/projects/elm/resume">resume</button></td></tr>'
            "</tbody></table></section>",
            fragment,
        )

    def test_should_lay_the_studies_in_a_table_and_leave_the_parked_orders_to_needs_you(self):
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
                        "last_run": "20261019T081500Z-d1",
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
            '<section class="block"><div class="block-head"><h2>Studies</h2><p>The studies that are due or stopped, and the scans holding new signals.</p></div><table><thead><tr><th>study</th><th>every</th><th>last run</th>'
            "<th>outcome</th><th>now</th><th>new signals</th></tr></thead><tbody>"
            "<tr><td>triage</td><td>24h</td><td>\u2013</td><td>\u2013</td><td>due, runs at the next tick</td>"
            "<td>\u2013</td></tr>"
            '<tr><td>debt</td><td>1d</td><td>10-19 08:15Z</td><td><span class="pill"><span class="tone tone-you"><span class="tone-shape" aria-hidden="true">▲</span>parked</span></span></td>'
            '<td>waits for <code class="cmd">brigade study run debt</code></td><td>\u2013</td></tr>'
            "</tbody></table></section>",
            fragment,
        )
        self.assertNotIn("<h2>Orders</h2>", fragment)


STALE_BRANCHES_SCAN = {"study": "stale_branches", "signals": 23, "oldest_age_s": 1468800}
WORKTREES_SCAN = {"study": "worktrees", "signals": 8, "oldest_age_s": 1296000}
STALE_BRANCHES_STUDY = {
    "name": "stale_branches",
    "every": "1d",
    "last_run": "20261018T080000Z-5b1a2c",
    "outcome": "done",
    "due": False,
}


class RenderHomeAsTheMockupTest(unittest.TestCase):
    def test_should_say_the_scans_holding_new_signals_are_parked_with_the_command_that_runs_one(self):
        # Arrange
        inbox = {"new_signals": 31, "scans": [STALE_BRANCHES_SCAN, WORKTREES_SCAN], "stalls": []}

        # Act
        fragment = render_home(create_home({"inbox": inbox}))

        # Assert
        self.assertIn(
            "<h3>2 scans are parked: stale_branches, worktrees</h3><p>31 new signals, the oldest 17d</p></div>"
            '<div class="act"><code class="cmd">brigade study run stale_branches</code></div>',
            fragment,
        )

    def test_should_show_a_wave_blocked_on_the_quota_as_blocked(self):
        # Act
        fragment = render_home(create_home({"waves": [OAK_W2_BLOCKED]}))

        # Assert
        self.assertIn(
            '<span class="pill"><span class="tone tone-you"><span class="tone-shape" aria-hidden="true">▲</span>blocked</span></span>',
            fragment,
        )

    def test_should_set_the_projects_and_their_pause_buttons_before_the_studies(self):
        # Act
        fragment = render_home(HOME)

        # Assert
        self.assertLess(fragment.index("<h2>Projects</h2>"), fragment.index("<h2>Studies</h2>"))

    def test_should_give_each_study_its_new_signals_and_the_day_of_its_last_run(self):
        # Arrange
        inbox = {"new_signals": 23, "scans": [STALE_BRANCHES_SCAN], "stalls": []}

        # Act
        fragment = render_home(create_home({"inbox": inbox, "studies": [STALE_BRANCHES_STUDY]}))

        # Assert
        self.assertIn("<th>new signals</th>", fragment)
        self.assertIn("<td>stale_branches</td><td>1d</td><td>10-18 08:00Z</td>", fragment)
        self.assertIn("<td>23</td>", fragment)
        self.assertNotIn("20261018T080000Z-5b1a2c", fragment)

    def test_should_link_each_count_of_the_last_24_hours_to_its_view_in_words_of_its_number(self):
        # Arrange
        home = HomeDocuments(
            status=STATUS,
            scheduler=FRESH_SCHEDULER,
            ledger={**QUIET_DAY, "events": {"wave.started": 1, "milestone.reported": 1}},
            inbox=EMPTY_INBOX,
            dry_run=NO_TASK_WAITING,
        )

        # Act
        fragment = render_home(home)

        # Assert
        self.assertIn('<a href="#waves">1 wave started</a>', fragment)
        self.assertIn('<a href="#reports">1 milestone reported</a>', fragment)


class RenderHomeLastDayTest(unittest.TestCase):
    def test_should_name_the_waves_started_in_the_last_24_hours(self):
        # Arrange
        home = HomeDocuments(
            status=STATUS,
            scheduler=FRESH_SCHEDULER,
            ledger={**QUIET_DAY, "waves_started": {"2026-10": ["oak_w3"]}},
            inbox=EMPTY_INBOX,
            dry_run=NO_TASK_WAITING,
        )

        # Act
        fragment = render_home(home)

        # Assert
        self.assertIn(
            '<li><a href="#waves">1 wave started</a> (<a href="#waves/oak_w3">oak_w3</a>), <a href="#waves">0 closed</a></li>',
            fragment,
        )

    def test_should_link_the_report_of_the_milestone_reported_in_the_last_24_hours(self):
        # Arrange
        home = HomeDocuments(
            status={**STATUS, "last_milestone_reported": M13_REACHED},
            scheduler=FRESH_SCHEDULER,
            ledger={**QUIET_DAY, "events": {"milestone.reported": 1}},
            inbox=EMPTY_INBOX,
            dry_run=NO_TASK_WAITING,
        )

        # Act
        fragment = render_home(home)

        # Assert
        self.assertIn(
            '<li><a href="#reports">1 milestone reported</a>: <a href="#reports/oak_M13">the report of M13</a></li>',
            fragment,
        )

    def test_should_link_no_report_of_a_milestone_reported_before_the_last_24_hours(self):
        # Arrange
        home = HomeDocuments(
            status={**STATUS, "last_milestone_reported": M13_REACHED | {"reported_at": "2026-10-18T08:59:00Z"}},
            scheduler=FRESH_SCHEDULER,
            ledger=QUIET_DAY,
            inbox=EMPTY_INBOX,
            dry_run=NO_TASK_WAITING,
        )

        # Act
        fragment = render_home(home)

        # Assert
        self.assertIn('<li><a href="#reports">0 milestones reported</a></li>', fragment)

    def test_should_break_the_run_segments_finished_down_by_how_they_ended(self):
        # Arrange
        segments = {"outcomes": {"done": 19, "handed_over": 3, "wall_limit": 2}, "error_classes": {}}
        home = HomeDocuments(
            status=STATUS,
            scheduler=FRESH_SCHEDULER,
            ledger={**QUIET_DAY, "events": {"run.finished": 24}, "segments": segments},
            inbox=EMPTY_INBOX,
            dry_run=NO_TASK_WAITING,
        )

        # Act
        fragment = render_home(home)

        # Assert
        self.assertIn(
            '<li><a href="#runs">24 run segments finished</a>: 19 done, 3 handed over, 2 wall limit</li>', fragment
        )

    def test_should_not_say_the_tick_is_healthy_when_the_scheduler_reports_it_stale(self):
        # Arrange
        home = HomeDocuments(
            status=STATUS, scheduler=STALE_SCHEDULER, ledger=QUIET_DAY, inbox=EMPTY_INBOX, dry_run=NO_TASK_WAITING
        )

        # Act
        fragment = render_home(home)

        # Assert
        self.assertNotIn("The tick is healthy", fragment)
