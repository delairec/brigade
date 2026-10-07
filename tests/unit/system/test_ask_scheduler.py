import unittest

from brigade.errors import BrigadeError
from brigade.system.ask_scheduler import SchedulerQuestion, ask_scheduler

NO_RUNTIME_NEEDED = None


class StatusReaderOmittingTheUnitFiles:
    def read_status(self, request: dict, runtime) -> dict:
        return {"schema_version": 1, "installed": False, "cron_line": None, "next_activation": None}


class AskSchedulerWhenTheAnswerBreaksItsShapeTest(unittest.TestCase):
    def test_should_refuse_the_answer_naming_the_plugin_and_the_operation(self):
        # Arrange
        question = SchedulerQuestion(scheduler_name="systemd", operation="read_status", request={})

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            ask_scheduler(StatusReaderOmittingTheUnitFiles(), question, NO_RUNTIME_NEEDED)

        # Assert
        self.assertEqual(
            str(refusal.exception), "scheduler plugin systemd answered read_status: lacks the key unit_files"
        )
