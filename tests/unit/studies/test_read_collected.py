import json
import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.studies.read_collected import read_collected

RUN_ID = "20261019T090000Z-aaaaaa"
JUDGE_STEP = {"kind": "judge", "slot": "report", "procedure": "study", "answer": "FINDING"}
OUTPUT_STEP = {"kind": "output", "output": "entity:FINDING"}
COLLECT_STEP = {"kind": "collect", "collector": "weather"}


class ReadCollectedTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.run_directory = Path(directory.name) / RUN_ID
        (self.run_directory / "steps").mkdir(parents=True)

    def test_should_read_the_evidence_of_the_collect_steps_in_the_order_of_their_rank(self):
        # Arrange
        (self.run_directory / "steps" / "10-collect.json").write_text(
            '{"collected": [{"collector": "corpus", "summary": {}, "collection": "/srv/corpus.json"}]}',
            encoding="utf-8",
        )
        (self.run_directory / "steps" / "2-collect.json").write_text(
            '{"collected": [{"collector": "ledger", "summary": {}, "collection": "/srv/ledger.json"}]}',
            encoding="utf-8",
        )

        # Act
        collected = read_collected(self.run_directory)

        # Assert
        self.assertEqual(
            collected,
            [
                {"collector": "ledger", "summary": {}, "collection": "/srv/ledger.json"},
                {"collector": "corpus", "summary": {}, "collection": "/srv/corpus.json"},
            ],
        )

    def test_should_read_no_evidence_for_a_run_whose_recipe_has_no_collect_step(self):
        # Arrange
        self.record_recipe([JUDGE_STEP, OUTPUT_STEP])

        # Act
        collected = read_collected(self.run_directory)

        # Assert
        self.assertEqual(collected, [])

    def test_should_refuse_a_run_whose_recipe_has_a_collect_step_not_yet_done(self):
        # Arrange
        self.record_recipe([COLLECT_STEP, JUDGE_STEP, OUTPUT_STEP])

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            read_collected(self.run_directory)

        # Assert
        self.assertEqual(str(refusal.exception), f"the run {RUN_ID} has collected no evidence yet")

    def record_recipe(self, steps: list[dict]) -> None:
        (self.run_directory / "order.json").write_text(
            json.dumps({"schema_version": 1, "order": {"name": "trees", "params": []}, "recipe": {"steps": steps}}),
            encoding="utf-8",
        )
