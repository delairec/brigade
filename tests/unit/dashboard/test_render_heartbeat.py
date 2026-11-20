import unittest
from datetime import UTC, datetime

from brigade.dashboard.render_heartbeat import render_heartbeat

NOW = datetime(2026, 11, 18, 22, 42, 40, tzinfo=UTC)
LAST_TICK = {"ts": "2026-11-18T22:30:27Z", "duration_ms": 30019, "actions_applied": 2}


class RenderHeartbeatTest(unittest.TestCase):
    def test_should_show_the_last_tick_and_its_age(self):
        # Arrange
        document = {"last_tick": LAST_TICK, "tick_stale_after": 15, "stale": False}

        # Act
        rendered = render_heartbeat(document, NOW)

        # Assert
        self.assertEqual(
            rendered,
            '<p class="heartbeat">Last tick <time datetime="2026-11-18T22:30:27Z">2026-11-18T22:30:27Z</time>,'
            " 12 min ago</p>",
        )

    def test_should_say_stale_when_the_scheduler_reports_it(self):
        # Arrange
        document = {"last_tick": LAST_TICK, "tick_stale_after": 10, "stale": True}

        # Act
        rendered = render_heartbeat(document, NOW)

        # Assert
        self.assertEqual(
            rendered,
            '<p class="heartbeat">Last tick <time datetime="2026-11-18T22:30:27Z">2026-11-18T22:30:27Z</time>,'
            ' 12 min ago <strong class="heartbeat-stale">stale</strong></p>',
        )

    def test_should_say_no_tick_ran_yet(self):
        # Arrange
        document = {"last_tick": None, "tick_stale_after": 15, "stale": False}

        # Act
        rendered = render_heartbeat(document, NOW)

        # Assert
        self.assertEqual(rendered, '<p class="heartbeat">No tick recorded yet</p>')
