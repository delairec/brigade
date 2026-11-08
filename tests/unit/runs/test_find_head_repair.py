import os
import tempfile
import unittest
from pathlib import Path

from brigade.runs.find_head_repair import HeadRepair, find_head_repair
from brigade.runs.record_run_pid import record_run_pid
from tests.unit.commands.run_directories import create_run_record, create_run_result, write_run

RED_HEAD = "8885daa"
OLDER_RUN = "20261018T100000Z-1a2b3c"
LATER_RUN = "20261018T110000Z-4d5e6f"
NO_RESULT = None


def describe_repair(run_id: str, head: str = RED_HEAD) -> dict:
    return {
        **create_run_record(run_id, None, None),
        "slot": "rebase",
        "arguments": {"branch": "integration/M4", "head": head},
    }


def finish(run_id: str, outcome: str) -> dict:
    return {
        **create_run_result(run_id, outcome, "2026-10-18T10:30:00Z"),
        "message": "Drop the flaky tide test?\nbrigade-end: blocked",
    }


class FindHeadRepairTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.state_root = Path(directory.name)
        (self.state_root / "runs").mkdir()

    def test_should_find_no_repair_of_a_head_no_run_repaired(self):
        # Arrange
        write_run(self.state_root, describe_repair(OLDER_RUN, head="4c0e214"), finish(OLDER_RUN, "blocked"))

        # Act
        repair = find_head_repair(self.state_root, "integration/M4", RED_HEAD)

        # Assert
        self.assertIsNone(repair)

    def test_should_find_the_live_repair_of_the_head(self):
        # Arrange
        record_run_pid(write_run(self.state_root, describe_repair(OLDER_RUN), NO_RESULT), os.getpid())

        # Act
        repair = find_head_repair(self.state_root, "integration/M4", RED_HEAD)

        # Assert
        self.assertEqual(repair, HeadRepair(run=OLDER_RUN, question=None))

    def test_should_find_no_repair_in_a_run_that_died_without_its_result(self):
        # Arrange
        write_run(self.state_root, describe_repair(OLDER_RUN), NO_RESULT)

        # Act
        repair = find_head_repair(self.state_root, "integration/M4", RED_HEAD)

        # Assert
        self.assertIsNone(repair)

    def test_should_find_the_question_of_a_repair_ended_blocked(self):
        # Arrange
        write_run(self.state_root, describe_repair(OLDER_RUN), finish(OLDER_RUN, "blocked"))

        # Act
        repair = find_head_repair(self.state_root, "integration/M4", RED_HEAD)

        # Assert
        self.assertEqual(repair, HeadRepair(run=OLDER_RUN, question="Drop the flaky tide test?"))

    def test_should_find_a_repair_ended_done_on_a_head_still_red(self):
        # Arrange
        write_run(self.state_root, describe_repair(OLDER_RUN), finish(OLDER_RUN, "done"))

        # Act
        repair = find_head_repair(self.state_root, "integration/M4", RED_HEAD)

        # Assert
        self.assertEqual(repair, HeadRepair(run=OLDER_RUN, question=None))

    def test_should_find_no_repair_in_a_run_that_failed(self):
        # Arrange
        write_run(self.state_root, describe_repair(OLDER_RUN), finish(OLDER_RUN, "failed"))

        # Act
        repair = find_head_repair(self.state_root, "integration/M4", RED_HEAD)

        # Assert
        self.assertIsNone(repair)

    def test_should_judge_the_head_by_its_latest_repair(self):
        # Arrange
        write_run(self.state_root, describe_repair(OLDER_RUN), finish(OLDER_RUN, "blocked"))
        write_run(self.state_root, describe_repair(LATER_RUN), finish(LATER_RUN, "failed"))

        # Act
        repair = find_head_repair(self.state_root, "integration/M4", RED_HEAD)

        # Assert
        self.assertIsNone(repair)

    def test_should_find_no_repair_in_a_run_of_another_slot(self):
        # Arrange
        write_run(self.state_root, {**describe_repair(OLDER_RUN), "slot": "build"}, finish(OLDER_RUN, "blocked"))

        # Act
        repair = find_head_repair(self.state_root, "integration/M4", RED_HEAD)

        # Assert
        self.assertIsNone(repair)
