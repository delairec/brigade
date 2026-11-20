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
HOME = HomeDocuments(status=STATUS, scheduler=FRESH_SCHEDULER, ledger=QUIET_DAY, inbox=EMPTY_INBOX)


def create_home(status_change: dict) -> HomeDocuments:
    return HomeDocuments(
        status={**STATUS, **status_change}, scheduler=FRESH_SCHEDULER, ledger=QUIET_DAY, inbox=EMPTY_INBOX
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
                    status={**STATUS, **status_change}, scheduler=scheduler, ledger=QUIET_DAY, inbox=EMPTY_INBOX
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

    def test_should_explain_the_sentence_by_what_waits_for_the_user(self):
        # Arrange
        rows = [
            ("nothing waits", {}, "<p>Nothing waits for you.</p></div>"),
            ("a halted wave", {"waves": [OAK_W2_BLOCKED]}, "<p>Waiting for you: 1, listed under Needs you.</p></div>"),
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
            inbox={**EMPTY_INBOX, "patterns": [{"name": "p1"}, {"name": "p2"}]},
        )

        # Act
        fragment = render_home(home)

        # Assert
        self.assertIn(
            '<section><h2>Needs you</h2><ul class="needs-you-list">'
            '<li class="needs-you tone-you"><span class="mark">II</span>'
            "<div><h3>Wave oak_w2 is halted</h3><p>blocked on quota until 2026-10-19T10:00:00Z</p></div>"
            '<div class="act"><code class="cmd">brigade wave resume oak_w2</code></div></li>'
            '<li class="needs-you tone-you"><span class="mark">?</span>'
            "<div><h3>2 proposed patterns wait for a decision</h3>"
            "<p>the inbox proposes them for ratification</p></div>"
            '<div class="act"><a class="btn btn-primary" href="#inbox">Decide in the inbox</a></div></li>'
            '<li class="needs-you tone-you"><span class="mark">?</span>'
            "<div><h3>1 scans hold new signals: corpus_lint_oak</h3><p>1 new signals, the oldest 15m</p></div>"
            '<div class="act"><a class="btn btn-primary" href="#inbox">Read the inbox</a></div></li>'
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
            '<section><h2>Needs you</h2><div class="empty-state"><p class="empty-why">nothing needs you</p>'
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
            '<div class="act"><a class="btn btn-primary" href="#inbox">Review</a></div></li></ul></section>',
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


class RenderHomeAtWorkTest(unittest.TestCase):
    def test_should_lay_each_open_wave_in_a_row_with_its_state_its_tasks_merged_and_its_live_run(self):
        # Arrange
        home = create_home({"live_runs": [LIVE_RUN_OF_E1]})

        # Act
        fragment = render_home(home)

        # Assert
        self.assertIn(
            "<section><h2>At work</h2><table><thead><tr><th>wave</th><th>state</th><th>tasks</th><th>live run</th>"
            '</tr></thead><tbody><tr><td><a href="#waves/elm_w1">elm_w1</a><br><span class="muted">elm</span></td>'
            '<td><span class="pill"><span class="tone tone-work"><span class="tone-shape" aria-hidden="true">●</span>running</span></span></td><td><svg class="segment-strip"',
            fragment,
        )
        self.assertIn(
            '</svg> <span class="muted num">0 of 3 merged</span></td>'
            '<td><a href="#runs/20261019T080000Z-e1">20261019T080000Z-e1</a><br><span class="muted">build · E1</span>'
            "</td></tr></tbody></table></section>",
            fragment,
        )

    def test_should_list_under_a_wave_its_own_live_runs_alone(self):
        # Arrange
        home = create_home({"waves": [ELM_W1, OAK_W2_BLOCKED], "live_runs": [LIVE_RUN_OF_E1]})

        # Act
        fragment = render_home(home)

        # Assert
        self.assertIn(
            '<span class="muted num">0 of 2 merged</span></td><td>\u2013</td></tr></tbody></table></section>', fragment
        )

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

    def test_should_count_what_the_last_24_hours_did_one_line_per_kind_of_work(self):
        # Arrange
        home = HomeDocuments(
            status=STATUS,
            scheduler=FRESH_SCHEDULER,
            ledger={"view": "overview", "events": {"tick.action_failed": 3}},
            inbox=EMPTY_INBOX,
        )

        # Act
        fragment = render_home(home)

        # Assert
        self.assertIn(
            '<section><h2>Last 24 hours</h2><ul class="lines">'
            '<li><b class="num">0</b> waves started, <b class="num">0</b> closed</li>'
            '<li><b class="num">0</b> pull requests opened, <b class="num">0</b> merged</li>'
            '<li><b class="num">0</b> milestones reported</li>'
            '<li><b class="num">0</b> run segments finished</li>'
            '<li><b class="num">3</b> failed tick actions</li></ul></section>',
            fragment,
        )

    def test_should_lay_the_projects_in_a_table_with_their_state_their_open_waves_and_their_button(self):
        # Act
        fragment = render_home(HOME)

        # Assert
        self.assertIn(
            "<section><h2>Projects</h2><table><thead><tr><th>project</th><th>state</th><th>open waves</th>"
            "<th></th></tr></thead><tbody>"
            '<tr><td>oak</td><td><span class="pill"><span class="tone tone-faint"><span class="tone-shape" aria-hidden="true">·</span>active</span></span></td><td>0</td>'
            '<td> <button type="button" data-post="/api/projects/oak/pause">pause</button></td></tr>'
            '<tr><td>elm</td><td><span class="pill"><span class="tone tone-you"><span class="tone-shape" aria-hidden="true">▲</span>paused</span></span></td><td>1</td>'
            '<td> <button type="button" data-post="/api/projects/elm/resume">resume</button></td></tr>'
            "</tbody></table></section>",
            fragment,
        )

    def test_should_lay_the_studies_in_a_routine_table_and_leave_the_parked_orders_to_needs_you(self):
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
            "<section><h2>Routine</h2><table><thead><tr><th>study</th><th>every</th><th>last run</th>"
            "<th>outcome</th><th>now</th></tr></thead><tbody>"
            "<tr><td>triage</td><td>24h</td><td>\u2013</td><td>\u2013</td><td>due, runs at the next tick</td></tr>"
            '<tr><td>debt</td><td>1d</td><td>r1</td><td><span class="pill"><span class="tone tone-you"><span class="tone-shape" aria-hidden="true">▲</span>parked</span></span></td>'
            '<td>waits for <code class="cmd">brigade study run debt</code></td></tr>'
            "</tbody></table></section>",
            fragment,
        )
        self.assertNotIn("<h2>Orders</h2>", fragment)
