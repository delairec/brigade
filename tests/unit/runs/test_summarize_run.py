import os
import tempfile
import unittest
from pathlib import Path

from brigade.runs.record_run_pid import record_run_pid
from brigade.runs.summarize_run import summarize_run
from tests.unit.runs.write_run_record import write_run_record
from tests.unit.runs.write_run_result import write_run_result

RUN_ID = "20261007T105605Z-396068"
NO_ARGUMENTS = {}


class SummarizeRunTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.run_directory = Path(directory.name) / "runs" / RUN_ID

    def write_segment(self, number: int, outcome: str, *, duration_ms: int | None, cost_usd: float | None) -> None:
        write_run_result(
            self.run_directory / "segments" / str(number) / "result.json",
            outcome,
            main_turns=30,
            duration_ms=duration_ms,
            cost_usd=cost_usd,
        )

    def test_should_sum_the_duration_and_the_cost_of_a_run_cut_at_the_wall_time_limit_and_resumed(self):
        # Arrange
        write_run_record(self.run_directory, {"task": "@TASK.B82", "base": "integration/oak"})
        self.write_segment(1, "wall_limit", duration_ms=1500000, cost_usd=1.5)
        self.write_segment(2, "done", duration_ms=600000, cost_usd=0.25)
        write_run_result(self.run_directory / "result.json", "done")

        # Act
        summary = summarize_run(self.run_directory)

        # Assert
        self.assertEqual(
            summary,
            {
                "run": RUN_ID,
                "procedure": "build-task",
                "slot": "build",
                "role": "builder",
                "project": None,
                "worktree": "/srv/tidepool",
                "state": "finished",
                "outcome": "done",
                "wave": None,
                "task": None,
                "started_at": "2026-10-07T10:56:05Z",
                "arguments": {"task": "@TASK.B82", "base": "integration/oak"},
                "segments": [
                    {"segment": 1, "outcome": "wall_limit", "turns": 30, "duration_ms": 1500000},
                    {"segment": 2, "outcome": "done", "turns": 30, "duration_ms": 600000},
                ],
                "duration_ms": 2100000,
                "cost_usd": 1.75,
                "duration_partial": False,
                "cost_partial": False,
            },
        )

    def test_should_mark_the_measures_partial_for_a_running_run_whose_first_segment_finished(self):
        # Arrange
        write_run_record(self.run_directory)
        self.write_segment(1, "handed_over", duration_ms=1500000, cost_usd=1.5)
        (self.run_directory / "segments" / "2").mkdir(parents=True)
        record_run_pid(self.run_directory, os.getpid())

        # Act
        summary = summarize_run(self.run_directory)

        # Assert
        self.assertEqual(
            summary,
            {
                "run": RUN_ID,
                "procedure": "build-task",
                "slot": "build",
                "role": "builder",
                "project": None,
                "worktree": "/srv/tidepool",
                "state": "running",
                "outcome": None,
                "wave": None,
                "task": None,
                "started_at": "2026-10-07T10:56:05Z",
                "arguments": NO_ARGUMENTS,
                "segments": [
                    {"segment": 1, "outcome": "handed_over", "turns": 30, "duration_ms": 1500000},
                    {"segment": 2, "outcome": None, "turns": None, "duration_ms": None},
                ],
                "duration_ms": 1500000,
                "cost_usd": 1.5,
                "duration_partial": True,
                "cost_partial": True,
            },
        )

    def test_should_mark_the_cost_alone_partial_when_one_segment_carries_no_cost(self):
        # Arrange
        write_run_record(self.run_directory)
        self.write_segment(1, "handed_over", duration_ms=1500000, cost_usd=None)
        self.write_segment(2, "done", duration_ms=600000, cost_usd=0.25)
        write_run_result(self.run_directory / "result.json", "done")

        # Act
        summary = summarize_run(self.run_directory)

        # Assert
        self.assertEqual(
            summary,
            {
                "run": RUN_ID,
                "procedure": "build-task",
                "slot": "build",
                "role": "builder",
                "project": None,
                "worktree": "/srv/tidepool",
                "state": "finished",
                "outcome": "done",
                "wave": None,
                "task": None,
                "started_at": "2026-10-07T10:56:05Z",
                "arguments": NO_ARGUMENTS,
                "segments": [
                    {"segment": 1, "outcome": "handed_over", "turns": 30, "duration_ms": 1500000},
                    {"segment": 2, "outcome": "done", "turns": 30, "duration_ms": 600000},
                ],
                "duration_ms": 2100000,
                "cost_usd": 0.25,
                "duration_partial": False,
                "cost_partial": True,
            },
        )

    def test_should_leave_the_measures_absent_when_no_segment_carries_them(self):
        # Arrange
        write_run_record(self.run_directory)
        self.write_segment(1, "failed", duration_ms=None, cost_usd=None)
        write_run_result(self.run_directory / "result.json", "failed")

        # Act
        summary = summarize_run(self.run_directory)

        # Assert
        self.assertEqual(
            summary,
            {
                "run": RUN_ID,
                "procedure": "build-task",
                "slot": "build",
                "role": "builder",
                "project": None,
                "worktree": "/srv/tidepool",
                "state": "finished",
                "outcome": "failed",
                "wave": None,
                "task": None,
                "started_at": "2026-10-07T10:56:05Z",
                "arguments": NO_ARGUMENTS,
                "segments": [{"segment": 1, "outcome": "failed", "turns": 30, "duration_ms": None}],
                "duration_ms": None,
                "cost_usd": None,
                "duration_partial": True,
                "cost_partial": True,
            },
        )

    def test_should_leave_the_measures_absent_and_whole_for_a_dead_run_without_segment(self):
        # Arrange
        write_run_record(self.run_directory)

        # Act
        summary = summarize_run(self.run_directory)

        # Assert
        self.assertEqual(
            summary,
            {
                "run": RUN_ID,
                "procedure": "build-task",
                "slot": "build",
                "role": "builder",
                "project": None,
                "worktree": "/srv/tidepool",
                "state": "dead",
                "outcome": None,
                "wave": None,
                "task": None,
                "started_at": "2026-10-07T10:56:05Z",
                "arguments": NO_ARGUMENTS,
                "segments": [],
                "duration_ms": None,
                "cost_usd": None,
                "duration_partial": False,
                "cost_partial": False,
            },
        )
