import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from brigade.commands.tick import _tick
from brigade.tick.run_rounds import RoundsOutcome


class TickWhenThePlanIsCappedTest(unittest.TestCase):
    def test_should_write_a_warning_to_stderr_when_the_plan_is_capped(self):
        # Arrange
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        runtime = mock.Mock()
        runtime.paths.state_root = Path(root.name)
        runtime.now = mock.Mock()
        outcome = RoundsOutcome(actions_applied=5, capped=True)
        stderr = io.StringIO()

        # Act
        with (
            mock.patch("brigade.commands.tick.hold_lock_without_waiting") as lock,
            mock.patch("brigade.commands.tick.run_rounds", return_value=outcome),
            mock.patch("brigade.commands.tick.write_json_atomically"),
            mock.patch("brigade.commands.tick.format_instant", return_value="2026-10-07T12:00:00Z"),
            contextlib.redirect_stderr(stderr),
        ):
            lock.return_value.__enter__ = mock.Mock(return_value=True)
            heartbeat = _tick(runtime)

        # Assert
        self.assertIsNotNone(heartbeat)
        self.assertIn("the plan was not empty after 10 rounds", stderr.getvalue())
