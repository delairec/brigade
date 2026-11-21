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
            '<p class="heartbeat"><span><span class="dot tone-done"></span><b>Tick alive</b></span>'
            '<span class="num">last <time datetime="2026-11-18T22:30:27Z">22:30:27Z</time>, 12 min ago</span>'
            '<span class="num">30.0 s · 2 actions</span></p>',
        )

    def test_should_say_stale_when_the_scheduler_reports_it(self):
        # Arrange
        document = {"last_tick": LAST_TICK, "tick_stale_after": 10, "stale": True}

        # Act
        rendered = render_heartbeat(document, NOW)

        # Assert
        self.assertEqual(
            rendered,
            '<p class="heartbeat"><span><span class="dot tone-failed"></span><b>Tick stale</b></span>'
            '<span class="num">last <time datetime="2026-11-18T22:30:27Z">22:30:27Z</time>, 12 min ago</span>'
            '<span class="num">30.0 s · 2 actions</span></p>',
        )

    def test_should_say_no_tick_ran_yet(self):
        # Arrange
        document = {"last_tick": None, "tick_stale_after": 15, "stale": False}

        # Act
        rendered = render_heartbeat(document, NOW)

        # Assert
        self.assertEqual(
            rendered,
            '<p class="heartbeat"><span><span class="dot tone-off"></span><b>No tick recorded yet</b></span></p>',
        )


class RenderHeartbeatOfItsSchedulerTest(unittest.TestCase):
    def test_should_name_the_scheduler_that_fires_the_tick_and_how_often(self):
        # Arrange
        document = {
            "scheduler": "systemd",
            "stale": False,
            "last_tick": {"ts": "2026-11-21T00:20:00Z", "duration_ms": 36774, "actions_applied": 2},
        }

        # Act
        heartbeat = render_heartbeat(document, datetime(2026, 11, 21, 0, 22, tzinfo=UTC))

        # Assert
        self.assertIn('<span class="faint">systemd timer, every 5 min</span></p>', heartbeat)
