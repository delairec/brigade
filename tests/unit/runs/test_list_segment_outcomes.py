import os
import tempfile
import unittest
from pathlib import Path

from brigade.runs.list_segment_outcomes import list_segment_outcomes
from brigade.runs.record_run_pid import record_run_pid
from brigade.runs.summarize_run import summarize_run
from tests.unit.runs.write_run_record import write_run_record
from tests.unit.runs.write_run_result import write_run_result

RUN_ID = "20261007T105605Z-396068"


def list_outcomes_of(run_directory: Path) -> list[str]:
    summary = summarize_run(run_directory)
    return list_segment_outcomes(summary["state"], summary["segments"])


class ListSegmentOutcomesTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.run_directory = Path(directory.name) / "runs" / RUN_ID
        write_run_record(self.run_directory)

    def write_segment(self, number: int, outcome: str) -> None:
        write_run_result(self.run_directory / "segments" / str(number) / "result.json", outcome)

    def finish_run(self, outcome: str) -> None:
        write_run_result(self.run_directory / "result.json", outcome)

    def test_should_name_the_cut_of_a_run_cut_at_the_wall_time_limit_and_resumed(self):
        # Arrange
        self.write_segment(1, "wall_limit")
        self.write_segment(2, "done")
        self.finish_run("done")

        # Act
        outcomes = list_outcomes_of(self.run_directory)

        # Assert
        self.assertEqual(outcomes, ["wall_limit", "done"])

    def test_should_name_each_handover_of_a_run_handed_over_twice(self):
        # Arrange
        self.write_segment(1, "handed_over")
        self.write_segment(2, "handed_over")
        self.write_segment(3, "done")
        self.finish_run("done")

        # Act
        outcomes = list_outcomes_of(self.run_directory)

        # Assert
        self.assertEqual(outcomes, ["handed_over", "handed_over", "done"])

    def test_should_end_on_running_for_a_running_run_whose_first_segment_finished(self):
        # Arrange
        self.write_segment(1, "handed_over")
        (self.run_directory / "segments" / "2").mkdir(parents=True)
        record_run_pid(self.run_directory, os.getpid())

        # Act
        outcomes = list_outcomes_of(self.run_directory)

        # Assert
        self.assertEqual(outcomes, ["handed_over", "running"])

    def test_should_end_on_dead_for_a_run_that_died_in_its_second_segment(self):
        # Arrange
        self.write_segment(1, "handed_over")
        (self.run_directory / "segments" / "2").mkdir(parents=True)

        # Act
        outcomes = list_outcomes_of(self.run_directory)

        # Assert
        self.assertEqual(outcomes, ["handed_over", "dead"])

    def test_should_name_nothing_for_a_finished_run_without_segment(self):
        # Arrange
        self.finish_run("done")

        # Act
        outcomes = list_outcomes_of(self.run_directory)

        # Assert
        self.assertEqual(outcomes, [])
