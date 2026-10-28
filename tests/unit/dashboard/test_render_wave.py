import unittest

from brigade.dashboard.render_wave import render_wave

SHOWN = {
    "schema_version": 1,
    "wave": "w4",
    "project": "oak",
    "branch": "integration/w4",
    "started_at": "2026-10-19T07:00:00Z",
    "last_event": "task.parked",
    "pull_request": None,
    "tasks": [
        {"task": "B27", "state": "merged", "pull_request": 235, "run": "r27", "reason": None},
        {"task": "B28", "state": "parked", "pull_request": None, "run": "r28", "reason": "blocked"},
        {"task": "B29", "state": "merged", "pull_request": 236, "run": "r29", "reason": None},
        {"task": "B30", "state": None, "pull_request": None, "run": None, "reason": None},
    ],
}
LEDGER = {
    "view": "wave",
    "wave": "w4",
    "rounds_by_task": {"B27": 2},
    "steps_by_task": {"B27": 40, "B28": 12, "B29": 9},
    "timeline": [
        {"at": "2026-10-19T07:00:00Z", "event": "wave.started", "fields": {"wave": "w4"}},
        {"at": "2026-10-19T08:00:00Z", "event": "task.parked", "fields": {"wave": "w4", "task": "B28"}},
    ],
}


class RenderWaveTest(unittest.TestCase):
    def test_should_group_the_tasks_by_state_and_date_the_timeline_oldest_first(self):
        # Act
        fragment = render_wave(SHOWN, LEDGER)

        # Assert
        self.assertEqual(
            fragment,
            "<section><h2>Wave w4 of oak</h2>"
            "<h3>merged</h3><ul>"
            "<li>B27, pull request 235, run r27, 2 rounds, 40 steps</li>"
            "<li>B29, pull request 236, run r29, 0 rounds, 9 steps</li>"
            "</ul>"
            "<h3>parked</h3><ul>"
            "<li>B28, pull request -, run r28, 0 rounds, 12 steps, blocked"
            ' <button type="button" data-post="/api/waves/w4/tasks/B28/requeue">requeue</button></li>'
            "</ul>"
            "<h3>queued</h3><ul>"
            "<li>B30, pull request -, run -, 0 rounds, - steps</li>"
            "</ul></section>"
            "<section><h2>Timeline</h2><ol>"
            "<li>2026-10-19T07:00:00Z wave.started</li>"
            "<li>2026-10-19T08:00:00Z task.parked B28</li>"
            "</ol></section>",
        )

    def test_should_escape_every_string_of_the_documents(self):
        # Arrange
        markup = "<script>alert(1)</script>"
        shown = {
            **SHOWN,
            "wave": markup,
            "project": markup,
            "tasks": [{"task": markup, "state": "parked", "pull_request": None, "run": markup, "reason": markup}],
        }
        ledger = {**LEDGER, "timeline": [{"at": markup, "event": markup, "fields": {"task": markup}}]}

        # Act
        fragment = render_wave(shown, ledger)

        # Assert
        self.assertNotIn("<script>", fragment)
