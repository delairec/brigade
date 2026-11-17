import tempfile
import unittest
from pathlib import Path

from brigade.recipes.create_output_performer import create_output_performer
from brigade.recipes.run_order import OrderRun

INBOX_OUTPUT_STEP = {"kind": "output", "output": "inbox"}
NO_OUTPUT_OF_THE_ORDER = None
ORDER_VALUES = {"pr": "12", "project": "shop"}
PULL_REQUEST_FILE_STEP = {"kind": "output", "output": "pr-file:{pr}:docs/reports/{pr}.md"}
JUDGED_ANSWER = 'RESULT triage_20261019T090000Z_20261019T090000Z_aaaaaa\n\tORDER "triage_20261019T090000Z"\n'


class OutputDouble:
    def __init__(self):
        self.kept: list[str] = []
        self.handed: list[tuple[str, Path]] = []

    def keep(self, answer: str) -> None:
        self.kept.append(answer)

    def hand(self, output: str, answer: Path) -> dict:
        self.handed.append((output, answer))
        return {"signal": "S12"}


class CreateOutputPerformerTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.run_directory = Path(temporary.name)
        self.run = OrderRun(
            order="triage_20261019T090000Z",
            project="shop",
            recipe={"name": "triage", "steps": [INBOX_OUTPUT_STEP]},
            run_id="20261019T090000Z-aaaaaa",
            run_directory=self.run_directory,
        )

    def test_should_keep_the_answer_the_judge_step_wrote_and_hand_it_to_the_output_of_the_step(self):
        # Arrange
        (self.run_directory / "answer.awawa").write_text(JUDGED_ANSWER, encoding="utf-8")
        output = OutputDouble()
        perform = create_output_performer(output.keep, output.hand, NO_OUTPUT_OF_THE_ORDER, ORDER_VALUES)

        # Act
        result = perform(INBOX_OUTPUT_STEP, self.run)

        # Assert
        self.assertEqual(
            result, {"output": "inbox", "answer": str(self.run_directory / "answer.awawa"), "signal": "S12"}
        )
        self.assertEqual(output.kept, [JUDGED_ANSWER])
        self.assertEqual(output.handed, [("inbox", self.run_directory / "answer.awawa")])

    def test_should_keep_the_answer_brigade_fills_when_no_judge_step_answered(self):
        # Arrange
        output = OutputDouble()
        perform = create_output_performer(output.keep, output.hand, NO_OUTPUT_OF_THE_ORDER, ORDER_VALUES)

        # Act
        perform(INBOX_OUTPUT_STEP, self.run)

        # Assert
        rendered = (
            "RESULT triage_20261019T090000Z_20261019T090000Z_aaaaaa\n"
            '\tORDER "triage_20261019T090000Z"\n'
            '\tRUN "20261019T090000Z-aaaaaa"\n'
        )
        self.assertEqual(output.kept, [rendered])
        self.assertEqual((self.run_directory / "answer.awawa").read_text(encoding="utf-8"), rendered)

    def test_should_hand_the_answer_to_the_output_the_order_names_over_that_of_the_step(self):
        # Arrange
        (self.run_directory / "answer.awawa").write_text(JUDGED_ANSWER, encoding="utf-8")
        output = OutputDouble()
        perform = create_output_performer(output.keep, output.hand, "issue", ORDER_VALUES)

        # Act
        perform(INBOX_OUTPUT_STEP, self.run)

        # Assert
        self.assertEqual(output.handed, [("issue", self.run_directory / "answer.awawa")])

    def test_should_hand_the_answer_to_the_output_of_the_step_filled_from_the_values_of_the_order(self):
        # Arrange
        (self.run_directory / "answer.awawa").write_text(JUDGED_ANSWER, encoding="utf-8")
        output = OutputDouble()
        perform = create_output_performer(output.keep, output.hand, NO_OUTPUT_OF_THE_ORDER, ORDER_VALUES)

        # Act
        perform(PULL_REQUEST_FILE_STEP, self.run)

        # Assert
        self.assertEqual(output.handed, [("pr-file:12:docs/reports/12.md", self.run_directory / "answer.awawa")])
