import unittest
from unittest import mock

from brigade.adapters.schedulers import systemd
from brigade.errors import BrigadeError
from brigade.system.ask_scheduler import SchedulerQuestion, ask_scheduler

NO_RUNTIME_NEEDED = None
STATUS_WITHOUT_ITS_UNIT_FILES = {"schema_version": 1, "installed": False, "cron_line": None, "next_activation": None}


class AskSchedulerWhenTheAnswerBreaksItsShapeTest(unittest.TestCase):
    def test_should_refuse_the_answer_naming_the_plugin_and_the_operation(self):
        # Arrange
        question = SchedulerQuestion(scheduler_name="systemd", operation="read_status", request={})

        # Act
        with (
            mock.patch.object(systemd, "read_status", return_value=STATUS_WITHOUT_ITS_UNIT_FILES),
            self.assertRaises(BrigadeError) as refusal,
        ):
            ask_scheduler(question, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(
            str(refusal.exception), "scheduler plugin systemd answered read_status: lacks the key unit_files"
        )
