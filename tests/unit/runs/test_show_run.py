import json
import shutil
import tempfile
import unittest
from pathlib import Path

from brigade.errors import BrigadeError
from brigade.runs.show_run import show_run
from tests.unit.runs.write_run_record import write_run_record
from tests.unit.runs.write_run_result import write_run_result

RUN_ID = "20261019T090000Z-c0ffee"
JOURNAL_LINE = (
    '{"schema_version": 1, "at": "2026-10-19T09:00:00Z", "segment": 1, "kind": "text",'
    ' "summary": "Reading the task", "cut": false}\n'
)

RUN_RECORD_WITHOUT_ITS_WAVE = {
    "schema_version": 1,
    "run": RUN_ID,
    "procedure": "build-task",
    "procedure_path": "built-in",
    "slot": "build",
    "role": "builder",
    "role_source": "built-in",
    "client": "fake",
    "project": None,
    "cwd": "/home/ada/tidepool",
    "worktree": "/home/ada/tidepool",
    "capabilities": ["read"],
    "budget": 40,
    "wall_limit_s": 1500.0,
    "arguments": {},
    "task": None,
    "brief": None,
}


class ShowRunTestCase(unittest.TestCase):
    def setUp(self):
        self.state_root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.state_root)
        self.run_directory = self.state_root / "runs" / RUN_ID
        write_run_record(self.run_directory)


class ShowRunOfAFinishedRunTest(ShowRunTestCase):
    def setUp(self):
        super().setUp()
        write_run_result(self.run_directory / "segments" / "1" / "result.json", "handed_over", main_steps=30)
        write_run_result(self.run_directory / "segments" / "2" / "result.json", "done", main_steps=12)
        write_run_result(self.run_directory / "result.json", "done", message="delivered #160")
        (self.run_directory / "journal.jsonl").write_text(JOURNAL_LINE)

    def test_should_show_the_run_its_message_and_each_segment(self):
        # Act
        document = show_run(self.state_root, RUN_ID, with_journal=False)

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "run": {
                    "run": RUN_ID,
                    "procedure": "build-task",
                    "slot": "build",
                    "role": "builder",
                    "project": None,
                    "worktree": "/home/ada/tidepool",
                    "state": "finished",
                    "outcome": "done",
                    "wave": None,
                    "task": None,
                    "message": "delivered #160",
                },
                "segments": [
                    {"segment": 1, "outcome": "handed_over", "steps": 30, "duration_ms": 1000},
                    {"segment": 2, "outcome": "done", "steps": 12, "duration_ms": 1000},
                ],
                "journal": None,
            },
        )

    def test_should_add_the_journal_when_asked(self):
        # Act
        document = show_run(self.state_root, RUN_ID, with_journal=True)

        # Assert
        self.assertEqual(
            document["journal"],
            [
                {
                    "schema_version": 1,
                    "at": "2026-10-19T09:00:00Z",
                    "segment": 1,
                    "kind": "text",
                    "summary": "Reading the task",
                    "cut": False,
                }
            ],
        )


class ShowRunOfARunStillInItsFirstSegmentTest(ShowRunTestCase):
    def test_should_show_a_segment_without_result_and_no_message(self):
        # Arrange
        (self.run_directory / "segments" / "1").mkdir(parents=True)

        # Act
        document = show_run(self.state_root, RUN_ID, with_journal=False)

        # Assert
        self.assertEqual(document["run"]["message"], None)
        self.assertEqual(document["segments"], [{"segment": 1, "outcome": None, "steps": None, "duration_ms": None}])

    def test_should_show_no_segment_before_the_first_starts(self):
        # Act
        document = show_run(self.state_root, RUN_ID, with_journal=False)

        # Assert
        self.assertEqual(document["segments"], [])

    def test_should_show_an_empty_journal_before_the_first_record(self):
        # Act
        document = show_run(self.state_root, RUN_ID, with_journal=True)

        # Assert
        self.assertEqual(document["journal"], [])


class ShowRunOfARunWrittenInAnotherShapeTest(ShowRunTestCase):
    def test_should_refuse_a_segment_result_of_an_older_shape_naming_the_file_and_its_version(self):
        # Arrange
        segment_result = self.run_directory / "segments" / "1" / "result.json"
        segment_result.parent.mkdir(parents=True)
        segment_result.write_text('{"schema_version": 1, "outcome": "done"}')

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            show_run(self.state_root, RUN_ID, with_journal=False)

        # Assert
        self.assertEqual(
            str(refusal.exception), f"{segment_result} is not a segment result: schema_version is 1, not one of 2"
        )

    def test_should_refuse_a_run_record_lacking_its_wave_naming_the_file_and_the_key(self):
        # Arrange
        run_record = self.run_directory / "run.json"
        run_record.write_text(json.dumps(RUN_RECORD_WITHOUT_ITS_WAVE))

        # Act
        with self.assertRaises(BrigadeError) as refusal:
            show_run(self.state_root, RUN_ID, with_journal=False)

        # Assert
        self.assertEqual(str(refusal.exception), f"{run_record} is not a run record: lacks the key wave")


class ShowRunOfNoRunTest(ShowRunTestCase):
    def test_should_refuse_an_id_naming_no_run_directory(self):
        for run_id in ["20261019T100000Z-0dd000", "../runs", f"../runs/{RUN_ID}"]:
            with self.subTest(run_id=run_id):
                # Act
                with self.assertRaises(BrigadeError) as refusal:
                    show_run(self.state_root, run_id, with_journal=False)

                # Assert
                self.assertEqual(str(refusal.exception), f"no run {run_id}")
