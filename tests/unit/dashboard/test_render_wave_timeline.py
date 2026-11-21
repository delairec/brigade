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
    def test_should_draw_a_state_the_task_waits_in_softer_than_one_it_works_in(self):
        # Arrange
        pr_open = {"at": "2026-10-19T08:30:00Z", "event": "task.state", "fields": {"task": "B28", "state": "pr_open"}}
        ledger = {**LEDGER, "events": [*LEDGER["events"][:3], pr_open, LEDGER["events"][3]]}

        # Act
        timeline = render_wave_timeline(ledger)

        # Assert
        self.assertRegex(timeline, r'<rect class="tone-review"[^>]* fill-opacity="0.45"[^>]*><title>B28 pr_open from')
        self.assertRegex(timeline, r'<rect class="tone-work"(?![^>]*fill-opacity)[^>]*><title>B28 running from')

    def test_should_draw_a_wave_of_one_instant(self):
        # Arrange
        at_start = {"at": "2026-10-19T07:00:00Z", "event": "task.state", "fields": {"task": "B27", "state": "running"}}
        ledger = {**LEDGER, "last": LEDGER["first"], "wall_time_ms": 0, "events": [LEDGER["events"][0], at_start]}

        # Act
        timeline = render_wave_timeline(ledger)

        # Assert
        self.assertIn("<title>B27 running from 07:00:00Z to 07:00:00Z, 0 s</title>", timeline)

    def test_should_end_a_task_on_a_tick_at_its_merge_and_not_on_a_bar_to_the_end_of_the_wave(self):
        # Arrange
        merged_early = {
            "at": "2026-10-19T08:00:00Z",
            "event": "task.state",
            "fields": {"task": "B27", "state": "merged"},
        }
        ledger = {**LEDGER, "events": [*LEDGER["events"][:3], merged_early]}

        # Act
        timeline = render_wave_timeline(ledger)

        # Assert
        self.assertRegex(
            timeline, r'<rect class="tone-done"[^>]* width="1"[^>]*><title>B27 merged at 08:00:00Z</title>'
        )

    def test_should_draw_a_halt_as_a_band_across_every_row(self):
        # Arrange
        halt = {"halted_at": "2026-10-19T08:00:00Z", "resumed_at": None}
        ledger = {**LEDGER, "halts": [halt]}

        # Act
        timeline = render_wave_timeline(ledger)

        # Assert
        self.assertRegex(
            timeline, r'<rect class="tone-you"[^>]*><title>wave halted from 08:00:00Z to 09:00:00Z</title>'
        )
