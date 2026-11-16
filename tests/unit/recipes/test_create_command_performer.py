import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.recipes.create_command_performer import create_command_performer
from brigade.recipes.run_order import OrderRun
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

SHOP = Path("/srv/shop")
NIGHTLY_RUN = OrderRun(
    order="nightly", project="shop", recipe={}, run_id="20261019T090000Z-aaaaaa", run_directory=Path("/srv/runs")
)
REPORT_STEP = {"kind": "command", "argv": ["make", "report", "PR={pull_request}", "{project}"]}


class CreateCommandPerformerTest(unittest.TestCase):
    def test_should_run_the_argv_of_the_step_in_the_project_with_its_values_substituted(self):
        # Arrange
        runner = RecordingProcessRunner(
            {("make", "report", "PR=12", "shop"): ProcessAnswer(stdout="written\n", stderr="slow\n")}
        )
        perform = create_command_performer(runner, SHOP, {"pull_request": "12", "project": "shop"})

        # Act
        result = perform(REPORT_STEP, NIGHTLY_RUN)

        # Assert
        self.assertEqual(result, {"argv": ["make", "report", "PR=12", "shop"], "exit_code": 0, "stdout": "written\n"})
        self.assertEqual(runner.commands, [("/srv/shop", ("make", "report", "PR=12", "shop"))])

    def test_should_fail_the_step_on_a_command_that_exits_non_zero(self):
        # Arrange
        runner = RecordingProcessRunner(
            {("make", "report", "PR=12", "shop"): ProcessAnswer(exit_code=2, stderr="no rule report\n")}
        )
        perform = create_command_performer(runner, SHOP, {"pull_request": "12", "project": "shop"})

        # Act
        with self.assertRaises(BrigadeError) as failure:
            perform(REPORT_STEP, NIGHTLY_RUN)

        # Assert
        self.assertEqual(str(failure.exception), "make report PR=12 shop exited 2: no rule report")
