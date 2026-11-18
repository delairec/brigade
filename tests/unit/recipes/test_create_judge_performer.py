import argparse
import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.recipes.create_judge_performer import create_judge_performer
from brigade.recipes.run_order import OrderRun

TRIAGE_JUDGE = {"kind": "judge", "slot": "judging", "procedure": "triage", "answer": "ANSWER"}
NO_ANSWER = None


class LaunchDouble:
    def __init__(self, answer: str | None, run_directory: Path):
        self.answer = answer
        self.run_directory = run_directory
        self.launches: list[argparse.Namespace] = []

    def launch(self, request: argparse.Namespace) -> dict:
        self.launches.append(request)
        if self.answer is not None:
            (self.run_directory / "answer.awawa").write_text(self.answer, encoding="utf-8")
        return {"run": "20261019T091500Z-bbbbbb"}


class CreateJudgePerformerTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.run_directory = Path(self.temporary.name)
        self.nightly_run = OrderRun(
            order="nightly",
            project="shop",
            recipe={"name": "triage"},
            run_id="20261019T090000Z-aaaaaa",
            run_directory=self.run_directory,
        )

    def tearDown(self):
        self.temporary.cleanup()

    def test_should_keep_the_judging_run_that_answered(self):
        # Arrange
        launcher = LaunchDouble("ANSWER nightly\n", self.run_directory)
        perform = create_judge_performer(launcher.launch)

        # Act
        result = perform(TRIAGE_JUDGE, self.nightly_run)

        # Assert
        self.assertEqual(result, {"run": "20261019T091500Z-bbbbbb"})

    def test_should_launch_the_procedure_of_the_step_on_its_slot_for_the_order_and_its_run(self):
        # Arrange
        launcher = LaunchDouble("ANSWER nightly\n", self.run_directory)
        perform = create_judge_performer(launcher.launch)

        # Act
        perform(TRIAGE_JUDGE, self.nightly_run)

        # Assert
        self.assertEqual(
            launcher.launches,
            [
                argparse.Namespace(
                    procedure="triage",
                    slot="judging",
                    project="shop",
                    cwd=None,
                    brief=None,
                    arguments=("order=nightly", "run=20261019T090000Z-aaaaaa"),
                    run_id=None,
                    wave=None,
                    task=None,
                    detach=False,
                    resume=False,
                    fallback=False,
                )
            ],
        )

    def test_should_fail_the_step_when_the_judging_run_gave_no_answer(self):
        # Arrange
        launcher = LaunchDouble(NO_ANSWER, self.run_directory)
        perform = create_judge_performer(launcher.launch)

        # Act
        with self.assertRaises(BrigadeError) as failure:
            perform(TRIAGE_JUDGE, self.nightly_run)

        # Assert
        self.assertEqual(str(failure.exception), "the judging run 20261019T091500Z-bbbbbb gave no answer")
