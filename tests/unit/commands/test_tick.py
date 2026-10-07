import argparse
import contextlib
import io
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest import mock

from brigade.commands import tick as tick_module
from brigade.commands.tick import tick
from brigade.runtime import Runtime
from brigade.system.paths import Paths
from brigade.tick.apply_actions import EXECUTORS


class LaunchRun:
    pass


def apply_nothing(action, runtime) -> None:
    return None


class TickWhosePlanNeverEmptiesTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        root = Path(self.root.name)
        self.runtime = Runtime(
            run_process=None,
            paths=Paths(
                config_root=root / "config" / "brigade",
                state_root=root / "state" / "brigade",
                cache_root=root / "cache" / "brigade",
                home=root,
                executable_search_path="",
            ),
            now=datetime(2026, 10, 7, 9, 0, tzinfo=UTC),
            entry_point=Path("/srv/brigade/bin/brigade"),
        )

    def test_should_warn_that_the_plan_was_still_not_empty_at_the_round_cap(self):
        # Arrange
        stderr = io.StringIO()

        # Act
        with (
            mock.patch.object(tick_module, "plan", return_value=(LaunchRun(),)),
            mock.patch.dict(EXECUTORS, {LaunchRun: apply_nothing}),
            contextlib.redirect_stderr(stderr),
        ):
            tick(argparse.Namespace(mode="once"), self.runtime)

        # Assert
        self.assertEqual(stderr.getvalue(), "brigade tick: the plan was not empty after 10 rounds\n")
