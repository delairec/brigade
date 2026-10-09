import tempfile
import unittest
from pathlib import Path

from brigade.runs.run_follower import RunFollower

LAST_RECORD_LINE = (
    '{"schema_version": 1, "at": "2026-10-09T14:00:04Z", "segment": 1, "kind": "result",'
    ' "summary": "done", "cut": false}\n'
)


def describe_a_run_ending_as_it_is_read(run_directory: Path) -> dict:
    with (run_directory / "journal.jsonl").open("a", encoding="utf-8") as journal:
        journal.write(LAST_RECORD_LINE)
    return {"run": "20261009T140000Z-abcdef", "state": "finished", "outcome": "done"}


class RunFollowerTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.run_directory = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def test_should_read_the_last_record_of_a_run_that_ends_while_it_reads_the_run(self):
        # Arrange
        follower = RunFollower(self.run_directory, describe_a_run_ending_as_it_is_read)

        # Act
        records = follower.read_records()

        # Assert
        self.assertEqual(
            (records, follower.run["state"]),
            (
                [
                    {
                        "schema_version": 1,
                        "at": "2026-10-09T14:00:04Z",
                        "segment": 1,
                        "kind": "result",
                        "summary": "done",
                        "cut": False,
                    }
                ],
                "finished",
            ),
        )
