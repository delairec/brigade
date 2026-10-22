import tempfile
import unittest
from pathlib import Path

from brigade.waves.read_planner_run import read_planner_run
from tests.unit.commands.run_directories import (
    create_planner_record,
    create_run_record,
    create_run_result,
    write_run,
)

FIRST_PLANNER_RUN = "20261013T140000Z-a10001"
OTHER_REQUEST_RUN = "20261013T150000Z-a10002"
DELIVERY_RUN = "20261013T160000Z-a10003"
LAST_PLANNER_RUN = "20261014T090000Z-a10004"
NO_RESULT = None


class ReadPlannerRunTest(unittest.TestCase):
    def setUp(self):
        self.state_root = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def test_should_find_no_planner_run_where_no_run_was_started(self):
        # Act
        planner = read_planner_run(self.state_root, "shop_r2")

        # Assert
        self.assertIsNone(planner)

    def test_should_find_no_planner_run_where_only_other_runs_were_started(self):
        # Arrange
        write_run(self.state_root, create_planner_record(OTHER_REQUEST_RUN, "shop_r3"), NO_RESULT)
        write_run(self.state_root, create_run_record(DELIVERY_RUN, "shop_w1", "S4"), NO_RESULT)

        # Act
        planner = read_planner_run(self.state_root, "shop_r2")

        # Assert
        self.assertIsNone(planner)

    def test_should_take_the_last_planner_run_of_the_request(self):
        # Arrange
        write_run(self.state_root, create_planner_record(FIRST_PLANNER_RUN, "shop_r2"), NO_RESULT)
        write_run(self.state_root, create_planner_record(OTHER_REQUEST_RUN, "shop_r3"), NO_RESULT)
        write_run(self.state_root, create_run_record(DELIVERY_RUN, "shop_w1", "S4"), NO_RESULT)
        write_run(self.state_root, create_planner_record(LAST_PLANNER_RUN, "shop_r2"), NO_RESULT)

        # Act
        planner = read_planner_run(self.state_root, "shop_r2")

        # Assert
        self.assertEqual(planner, {"run": LAST_PLANNER_RUN, "state": "dead"})

    def test_should_give_the_outcome_of_a_finished_planner_run(self):
        # Arrange
        failed = create_run_result(LAST_PLANNER_RUN, "failed", "2026-10-14T09:20:00Z")
        write_run(self.state_root, create_planner_record(LAST_PLANNER_RUN, "shop_r2"), failed)

        # Act
        planner = read_planner_run(self.state_root, "shop_r2")

        # Assert
        self.assertEqual(planner, {"run": LAST_PLANNER_RUN, "state": "failed"})

    def test_should_pass_over_a_run_whose_record_is_unreadable(self):
        # Arrange
        write_run(self.state_root, create_planner_record(FIRST_PLANNER_RUN, "shop_r2"), NO_RESULT)
        unreadable = self.state_root / "runs" / LAST_PLANNER_RUN
        unreadable.mkdir()
        (unreadable / "run.json").write_text("{", encoding="utf-8")

        # Act
        planner = read_planner_run(self.state_root, "shop_r2")

        # Assert
        self.assertEqual(planner, {"run": FIRST_PLANNER_RUN, "state": "dead"})

    def test_should_pass_over_a_run_directory_that_holds_no_record_yet(self):
        # Arrange
        write_run(self.state_root, create_planner_record(FIRST_PLANNER_RUN, "shop_r2"), NO_RESULT)
        (self.state_root / "runs" / LAST_PLANNER_RUN).mkdir()

        # Act
        planner = read_planner_run(self.state_root, "shop_r2")

        # Assert
        self.assertEqual(planner, {"run": FIRST_PLANNER_RUN, "state": "dead"})


if __name__ == "__main__":
    unittest.main()
