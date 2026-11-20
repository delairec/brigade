import unittest

from brigade.dashboard.render_wave_timeline import render_wave_timeline

LEDGER = {
    "wave": "w4",
    "first": "2026-10-19T07:00:00Z",
    "last": "2026-10-19T09:00:00Z",
    "wall_time_ms": 7200000,
    "tasks": ["B27", "B28"],
    "halts": [],
    "events": [
        {"at": "2026-10-19T07:00:00Z", "event": "wave.started", "fields": {"wave": "w4"}},
        {"at": "2026-10-19T07:30:00Z", "event": "task.state", "fields": {"task": "B27", "state": "running"}},
        {"at": "2026-10-19T08:00:00Z", "event": "task.state", "fields": {"task": "B28", "state": "running"}},
        {"at": "2026-10-19T09:00:00Z", "event": "task.state", "fields": {"task": "B27", "state": "merged"}},
    ],
}


class RenderWaveTimelineTest(unittest.TestCase):
    def test_should_place_each_state_of_a_task_on_its_row_over_the_time_of_the_wave(self):
        # Act
        timeline = render_wave_timeline(LEDGER)

        # Assert
        self.assertEqual(
            timeline,
            '<svg class="timeline" viewBox="0 0 120 24" role="img" aria-label="How the wave w4 went">'
            '<text class="timeline-label" x="0" y="6">B27</text>'
            '<circle class="timeline-mark tone-work" cx="45" cy="6" r="2"><title>B27 running at 2026-10-19T07:30:00Z</title></circle>'
            '<circle class="timeline-mark tone-done" cx="120" cy="6" r="2"><title>B27 merged at 2026-10-19T09:00:00Z</title></circle>'
            '<text class="timeline-label" x="0" y="18">B28</text>'
            '<circle class="timeline-mark tone-work" cx="70" cy="18" r="2"><title>B28 running at 2026-10-19T08:00:00Z</title></circle>'
            "</svg>",
        )

    def test_should_draw_a_halt_as_a_band_across_every_row(self):
        # Arrange
        ledger = {
            **LEDGER,
            "halts": [
                {"halted_at": "2026-10-19T07:30:00Z", "resumed_at": "2026-10-19T08:00:00Z", "duration_ms": 1800000}
            ],
        }

        # Act
        timeline = render_wave_timeline(ledger)

        # Assert
        self.assertIn(
            '<rect class="halt-band" x="45" y="0" width="25" height="24">'
            "<title>halted from 2026-10-19T07:30:00Z to 2026-10-19T08:00:00Z</title></rect>",
            timeline,
        )

    def test_should_draw_a_halt_not_resumed_up_to_the_last_event_of_the_wave(self):
        # Arrange
        ledger = {**LEDGER, "halts": [{"halted_at": "2026-10-19T08:00:00Z", "resumed_at": None, "duration_ms": None}]}

        # Act
        timeline = render_wave_timeline(ledger)

        # Assert
        self.assertIn(
            '<rect class="halt-band" x="70" y="0" width="50" height="24">'
            "<title>halted from 2026-10-19T08:00:00Z, not resumed</title></rect>",
            timeline,
        )

    def test_should_place_every_mark_at_the_start_of_a_wave_of_one_instant(self):
        # Arrange
        instant = "2026-10-19T07:00:00Z"
        ledger = {
            **LEDGER,
            "last": instant,
            "wall_time_ms": 0,
            "tasks": ["B27"],
            "events": [{"at": instant, "event": "task.state", "fields": {"task": "B27", "state": "running"}}],
        }

        # Act
        timeline = render_wave_timeline(ledger)

        # Assert
        self.assertIn('cx="20" cy="6"', timeline)

    def test_should_escape_a_task_name_holding_markup(self):
        # Arrange
        markup = "<script>alert(1)</script>"
        ledger = {
            **LEDGER,
            "wave": markup,
            "tasks": [markup],
            "events": [{"at": LEDGER["last"], "event": "task.state", "fields": {"task": markup, "state": markup}}],
        }

        # Act
        timeline = render_wave_timeline(ledger)

        # Assert
        self.assertNotIn("<script>", timeline)
