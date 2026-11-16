import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.recipes.find_answer_type import find_answer_type
from brigade.recipes.run_order import OrderRun

COLLECT_STEP = {"kind": "collect", "collector": "open-issues"}
FIRST_JUDGE = {"kind": "judge", "slot": "judging", "procedure": "triage", "answer": "RESULT"}
SECOND_JUDGE = {"kind": "judge", "slot": "review", "procedure": "review-pr", "answer": "REPORT"}


class FindAnswerTypeTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.run_directory = Path(temporary.name)
        (self.run_directory / "steps").mkdir()

    def create_run(self, steps: list[dict]) -> OrderRun:
        return OrderRun(
            order="nightly",
            project=None,
            recipe={"name": "triage", "steps": steps},
            run_id="20261019T090000Z-aaaaaa",
            run_directory=self.run_directory,
        )

    def test_should_name_the_answer_of_the_first_judge_step_not_done(self):
        # Arrange
        run = self.create_run([COLLECT_STEP, FIRST_JUDGE, SECOND_JUDGE])
        (self.run_directory / "steps" / "2-judge.json").write_text("{}", encoding="utf-8")

        # Act
        answer_type = find_answer_type(run)

        # Assert
        self.assertEqual(answer_type, "REPORT")

    def test_should_refuse_a_run_whose_judge_steps_are_all_done(self):
        # Arrange
        run = self.create_run([COLLECT_STEP, FIRST_JUDGE])
        (self.run_directory / "steps" / "2-judge.json").write_text("{}", encoding="utf-8")

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            find_answer_type(run)

        # Assert
        self.assertEqual(str(refusal.exception), "the run 20261019T090000Z-aaaaaa waits for no judge step")
