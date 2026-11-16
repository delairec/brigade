import json
import tempfile
import unittest
from pathlib import Path

from brigade.recipes.render_result import render_result
from brigade.recipes.run_order import OrderRun

OPEN_ISSUES_STEP = {"kind": "collect", "collector": "open-issues"}
FAILING_TESTS_STEP = {"kind": "collect", "collector": "failing-tests"}
TRIAGE_JUDGE = {"kind": "judge", "slot": "judging", "procedure": "triage", "answer": "RESULT"}


class RenderResultTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.run_directory = Path(temporary.name)
        (self.run_directory / "steps").mkdir()

    def create_run(self, steps: list[dict]) -> OrderRun:
        return OrderRun(
            order="triage_20261019T090000Z",
            project="shop",
            recipe={"name": "triage", "steps": steps},
            run_id="20261019T090000Z-aaaaaa",
            run_directory=self.run_directory,
        )

    def write_step(self, name: str, result: dict) -> None:
        (self.run_directory / "steps" / f"{name}.json").write_text(json.dumps(result), encoding="utf-8")

    def test_should_fill_the_order_its_run_and_what_each_collect_step_gave(self):
        # Arrange
        run = self.create_run([OPEN_ISSUES_STEP, TRIAGE_JUDGE])
        self.write_step(
            "1-collect", {"collector": "open-issues", "summary": {"open": 2}, "document": "/srv/open/document.json"}
        )

        # Act
        result = render_result(run)

        # Assert
        self.assertEqual(
            result,
            "RESULT triage_20261019T090000Z_20261019T090000Z_aaaaaa\n"
            '\tORDER "triage_20261019T090000Z"\n'
            '\tRUN "20261019T090000Z-aaaaaa"\n'
            '\tCOLLECTED "open-issues"\n'
            '\t\tSUMMARY "{\\"open\\": 2}"\n'
            '\t\tDOCUMENT "/srv/open/document.json"\n',
        )

    def test_should_leave_out_a_collect_step_that_was_skipped(self):
        # Arrange
        run = self.create_run([FAILING_TESTS_STEP, OPEN_ISSUES_STEP])
        self.write_step("1-collect", {"skipped": "collector failing-tests exited 1"})
        self.write_step("2-collect", {"collector": "open-issues", "summary": {}, "document": "/srv/document.json"})

        # Act
        result = render_result(run)

        # Assert
        self.assertEqual(
            result,
            "RESULT triage_20261019T090000Z_20261019T090000Z_aaaaaa\n"
            '\tORDER "triage_20261019T090000Z"\n'
            '\tRUN "20261019T090000Z-aaaaaa"\n'
            '\tCOLLECTED "open-issues"\n'
            '\t\tSUMMARY "{}"\n'
            '\t\tDOCUMENT "/srv/document.json"\n',
        )
