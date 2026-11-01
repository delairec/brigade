import unittest

from brigade.dashboard.render_home import render_home

NO_USAGE = {"input_tokens": 0, "output_tokens": 0, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}
HOME = {
    "schema_version": 1,
    "projects": [{"name": "oak", "paused": False}, {"name": "elm", "paused": True}],
    "waves": [
        {
            "wave": "oak_w2",
            "project": "oak",
            "branch": "integration/oak_w2",
            "last_event": "wave.paused",
            "tasks": 2,
            "pause": {"reason": "quota", "resume_at": "2026-10-19T10:00:00Z"},
        },
        {
            "wave": "elm_w1",
            "project": "elm",
            "branch": "integration/elm_w1",
            "last_event": "wave.started",
            "tasks": 1,
            "pause": None,
        },
    ],
    "inbox": {"new_signals": 3, "scans": []},
    "quota": {
        "window_hours": 5,
        "usage": {
            "input_tokens": 10,
            "output_tokens": 20,
            "cache_creation_input_tokens": 30,
            "cache_read_input_tokens": 40,
        },
        "runs_without_usage": 1,
        "paused_waves": [{"wave": "oak_w2", "resume_at": "2026-10-19T10:00:00Z"}],
    },
    "last_tick": None,
    "studies": [{"name": "triage", "status": "active", "every": "24h", "last_run": None, "outcome": None, "due": True}],
}


class RenderHomeTest(unittest.TestCase):
    def test_should_render_each_section_of_the_home_document_with_its_actions(self):
        # Act
        fragment = render_home(HOME)

        # Assert
        self.assertEqual(
            fragment,
            "<section><h2>Projects</h2><ul>"
            '<li>oak, active <button type="button" data-post="/api/projects/oak/pause">pause</button></li>'
            '<li>elm, paused <button type="button" data-post="/api/projects/elm/resume">resume</button></li>'
            "</ul></section>"
            "<section><h2>Waves</h2><ul>"
            '<li><a href="#waves/oak_w2">oak_w2</a> of oak, wave.paused,'
            " paused on quota until 2026-10-19T10:00:00Z"
            ' <button type="button" data-post="/api/waves/oak_w2/resume">resume</button></li>'
            '<li><a href="#waves/elm_w1">elm_w1</a> of elm, wave.started</li>'
            "</ul></section>"
            "<section><h2>Inbox</h2><p>3 new signals</p><ul></ul></section>"
            "<section><h2>Quota</h2><p>over the last 5 hours, 1 runs without usage</p><dl>"
            "<dt>input_tokens</dt><dd>10</dd><dt>output_tokens</dt><dd>20</dd>"
            "<dt>cache_creation_input_tokens</dt><dd>30</dd><dt>cache_read_input_tokens</dt><dd>40</dd>"
            "</dl><ul><li>oak_w2 paused on quota until 2026-10-19T10:00:00Z</li></ul></section>"
            "<section><h2>Last tick</h2><p>never</p></section>"
            "<section><h2>Studies</h2><ul><li>triage, due</li></ul></section>",
        )

    def test_should_render_the_last_tick_and_a_parked_study(self):
        # Arrange
        document = {
            **HOME,
            "last_tick": {"ts": "2026-10-19T08:55:00Z", "duration_ms": 120, "actions_applied": 2},
            "studies": [
                {"name": "debt", "status": "active", "every": "1d", "last_run": "r1", "outcome": "parked", "due": False}
            ],
        }

        # Act
        fragment = render_home(document)

        # Assert
        self.assertIn("<section><h2>Last tick</h2><p>2026-10-19T08:55:00Z, 2 actions applied in 120 ms</p>", fragment)
        self.assertIn("<section><h2>Studies</h2><ul><li>debt, parked</li></ul></section>", fragment)

    def test_should_render_each_scan_holding_new_signals_with_their_count_and_the_age_of_the_oldest(self):
        # Arrange
        document = {
            **HOME,
            "inbox": {
                "new_signals": 3,
                "scans": [
                    {"study": "corpus_lint_oak", "signals": 2, "oldest_age_s": 7200},
                    {"study": "stale_branches_elm", "signals": 1, "oldest_age_s": 900},
                ],
            },
        }

        # Act
        fragment = render_home(document)

        # Assert
        self.assertIn(
            "<section><h2>Inbox</h2><p>3 new signals</p><ul>"
            "<li>corpus_lint_oak, 2 new signals, the oldest 2h</li>"
            "<li>stale_branches_elm, 1 new signals, the oldest 15m</li>"
            "</ul></section>",
            fragment,
        )

    def test_should_render_a_wave_paused_until_further_notice_without_a_resume_time(self):
        # Arrange
        document = {
            **HOME,
            "waves": [
                {
                    "wave": "elm_w1",
                    "project": "elm",
                    "branch": "integration/elm_w1",
                    "last_event": "wave.paused",
                    "tasks": 1,
                    "pause": {"reason": "forge_account", "resume_at": None},
                }
            ],
        }

        # Act
        fragment = render_home(document)

        # Assert
        self.assertIn(
            '<li><a href="#waves/elm_w1">elm_w1</a> of elm, wave.paused, paused on forge_account'
            ' <button type="button" data-post="/api/waves/elm_w1/resume">resume</button></li>',
            fragment,
        )

    def test_should_escape_every_string_of_the_document(self):
        # Arrange
        markup = "<script>alert(1)</script>"
        document = {
            **HOME,
            "projects": [{"name": markup, "paused": False}],
            "waves": [{**HOME["waves"][0], "wave": markup, "project": markup, "last_event": markup}],
            "inbox": {"new_signals": 1, "scans": [{"study": markup, "signals": 1, "oldest_age_s": 60}]},
            "quota": {**HOME["quota"], "usage": NO_USAGE, "paused_waves": [{"wave": markup, "resume_at": markup}]},
            "studies": [{**HOME["studies"][0], "name": markup}],
        }

        # Act
        fragment = render_home(document)

        # Assert
        self.assertNotIn("<script>", fragment)
