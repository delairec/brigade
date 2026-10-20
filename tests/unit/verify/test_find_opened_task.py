import tempfile
import unittest
from pathlib import Path

from brigade.ledger.task_pr_opened import TaskPrOpened
from brigade.verify.find_opened_task import OpenedTask, find_opened_task
from tests.unit.commands.command_runtime import create_runtime, write_ledger
from tests.unit.commands.test_verify_preflight import TASK_PR_OPENED, WAVE_STARTED

LATER_WAVE_STARTED = {**WAVE_STARTED, "ts": "2026-10-02T22:00:00Z", "wave": "tidepool_w17", "branch": "integration/M5"}
REOPENED_IN_THE_LATER_WAVE = {**TASK_PR_OPENED, "ts": "2026-10-03T22:00:00Z", "wave": "tidepool_w17"}


class FindOpenedTaskTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def test_should_find_the_task_of_the_last_opening_of_a_pull_request_opened_twice(self):
        # Arrange
        write_ledger(self.root, [WAVE_STARTED, TASK_PR_OPENED, LATER_WAVE_STARTED, REOPENED_IN_THE_LATER_WAVE])

        # Act
        found = find_opened_task(create_runtime(self.root), "tidepool", 42)

        # Assert
        self.assertEqual(
            found,
            OpenedTask(
                opened=TaskPrOpened(
                    project="tidepool",
                    task="T7",
                    wave="tidepool_w17",
                    branch="task/M4-tides/T7",
                    pr=42,
                    login="tidepool-bot",
                ),
                wave_branch="integration/M5",
            ),
        )
