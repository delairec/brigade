import unittest
from unittest import mock

from brigade.errors import BrigadeError
from brigade.system.ask_scheduler import SchedulerQuestion, ask_scheduler


class AskSchedulerTest(unittest.TestCase):
    def test_should_raise_when_the_scheduler_answer_is_invalid(self):
        # Arrange
        scheduler = mock.Mock()
        scheduler.install.return_value = {"wrong": "shape"}
        runtime = mock.Mock()
        question = SchedulerQuestion(scheduler_name="cron", operation="install", request={})

        # Act
        with (
            mock.patch("brigade.system.ask_scheduler.resolve_plugin", return_value=scheduler),
            self.assertRaises(BrigadeError) as raised,
        ):
            ask_scheduler(question, runtime)

        # Assert
        self.assertIn("scheduler plugin cron answered install", str(raised.exception))

    def test_should_return_the_answer_when_it_is_valid(self):
        # Arrange
        scheduler = mock.Mock()
        scheduler.install.return_value = {
            "schema_version": 1,
            "scheduler": "cron",
            "unit_files": [],
            "cron_line": "*/5 * * * * brigade tick --once",
            "keep_running": None,
        }
        runtime = mock.Mock()
        question = SchedulerQuestion(scheduler_name="cron", operation="install", request={})

        # Act
        with mock.patch("brigade.system.ask_scheduler.resolve_plugin", return_value=scheduler):
            answer = ask_scheduler(question, runtime)

        # Assert
        self.assertEqual(answer["scheduler"], "cron")
