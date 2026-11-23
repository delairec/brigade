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

    def test_should_mark_each_whole_hour_inside_the_wave_on_its_axis_with_a_grid_line(self):
        # Arrange
        ledger = {**LEDGER, "first": "2026-10-19T06:30:00Z", "wall_time_ms": 9000000}

        # Act
        timeline = render_wave_timeline(ledger)

        # Assert
        self.assertIn(
            '<line class="g-grid" x1="204.6" y1="8" x2="204.6" y2="64"></line>'
            '<line class="g-grid" x1="493.8" y1="8" x2="493.8" y2="64"></line>',
            timeline,
        )
        self.assertIn(
            '<text class="g-text" x="60" y="80">06:30:00Z</text>'
            '<text class="g-text" x="204.6" y="80" text-anchor="middle">07:00</text>'
            '<text class="g-text" x="493.8" y="80" text-anchor="middle">08:00</text>'
            '<text class="g-text" x="783" y="80" text-anchor="end">09:00:00Z</text>',
            timeline,
        )

    def test_should_mark_no_hour_on_the_axis_of_a_wave_that_starts_and_ends_on_one(self):
        # Arrange
        within_one_hour = {**LEDGER, "last": "2026-10-19T08:00:00Z", "wall_time_ms": 3600000}

        # Act
        timeline = render_wave_timeline(within_one_hour)

        # Assert
        self.assertNotIn('text-anchor="middle"', timeline)

    def test_should_draw_no_grid_line_on_the_hour_a_wave_ends_on(self):
        # Arrange
        ending_on_the_hour = {
            **LEDGER,
            "first": "2026-10-19T07:30:00Z",
            "last": "2026-10-19T08:00:00Z",
            "wall_time_ms": 1800000,
        }

        # Act
        timeline = render_wave_timeline(ending_on_the_hour)

        # Assert
        self.assertNotIn('class="g-grid"', timeline)

    def test_should_keep_the_grid_line_but_not_the_label_of_an_hour_too_close_to_the_start_or_the_end_label(self):
        # Arrange
        ledger = {**LEDGER, "first": "2026-10-19T06:55:00Z", "last": "2026-10-19T09:03:00Z", "wall_time_ms": 7680000}

        # Act
        timeline = render_wave_timeline(ledger)

        # Assert
        self.assertIn('<line class="g-grid" x1="88.2" y1="8" x2="88.2" y2="64"></line>', timeline)
        self.assertIn('<line class="g-grid" x1="766.1" y1="8" x2="766.1" y2="64"></line>', timeline)
        self.assertIn(
            '<text class="g-text" x="60" y="80">06:55:00Z</text>'
            '<text class="g-text" x="427.1" y="80" text-anchor="middle">08:00</text>'
            '<text class="g-text" x="783" y="80" text-anchor="end">09:03:00Z</text>',
            timeline,
        )
