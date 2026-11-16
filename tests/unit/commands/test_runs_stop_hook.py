import argparse
import unittest
from datetime import UTC, datetime

from brigade.commands.runs_stop_hook import COMMAND, runs_stop_hook
from tests.unit.create_test_runtime import create_test_runtime

SOFT_LIMIT_EPOCH = 1791364980
PAST_THE_SOFT_LIMIT = datetime(2026, 10, 7, 9, 23, 0, tzinfo=UTC)
BEFORE_THE_SOFT_LIMIT = datetime(2026, 10, 7, 9, 22, 59, tzinfo=UTC)


class RunsStopHookTest(unittest.TestCase):
    def test_should_stop_the_session_once_its_soft_limit_has_passed(self):
        # Arrange
        runtime = create_test_runtime(now=PAST_THE_SOFT_LIMIT)

        # Act
        document = runs_stop_hook(argparse.Namespace(at=SOFT_LIMIT_EPOCH), runtime)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "stop": {"continue": False, "stopReason": "the soft limit 2026-10-07T09:23:00Z has passed"},
            },
        )

    def test_should_leave_the_session_running_before_its_soft_limit(self):
        # Arrange
        runtime = create_test_runtime(now=BEFORE_THE_SOFT_LIMIT)

        # Act
        document = runs_stop_hook(argparse.Namespace(at=SOFT_LIMIT_EPOCH), runtime)

        # Assert
        self.assertEqual(document, {"schema_version": 1, "stop": None})


class RunsStopHookTextTest(unittest.TestCase):
    def test_should_print_the_stop_document_as_json(self):
        # Arrange
        document = {
            "schema_version": 1,
            "stop": {"continue": False, "stopReason": "the soft limit 2026-10-07T09:23:00Z has passed"},
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, '{"continue": false, "stopReason": "the soft limit 2026-10-07T09:23:00Z has passed"}')

    def test_should_print_nothing_before_the_soft_limit(self):
        # Arrange
        no_stop = {"schema_version": 1, "stop": None}

        # Act
        text = COMMAND.render_text(no_stop)

        # Assert
        self.assertEqual(text, "")
