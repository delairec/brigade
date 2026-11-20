import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.run_list import COMMAND
from tests.unit.commands.run_directories import (
    FIRST_RUN,
    SECOND_RUN,
    THIRD_RUN,
    create_run_record,
    create_run_result,
    write_run,
)
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

ANY_WAVE = None
ANY_TASK = None
ANY_STATE = None
NO_ARGUMENTS = {}
FIRST_LISTED = {
    "run": FIRST_RUN,
    "procedure": "deliver",
    "slot": "build",
    "role": "builder",
    "project": None,
    "worktree": "/srv/tidepool",
    "state": "finished",
    "outcome": "done",
    "wave": "tidepool_w1",
    "task": "T1",
    "started_at": "2026-10-07T09:00:00Z",
    "arguments": NO_ARGUMENTS,
    "segments": [{"segment": 1, "outcome": "done", "turns": 12, "duration_ms": 4200}],
    "duration_ms": 4200,
    "cost_usd": None,
    "duration_partial": False,
    "cost_partial": True,
}
DEAD_LISTED = {
    "run": THIRD_RUN,
    "procedure": "deliver",
    "slot": "build",
    "role": "builder",
    "project": None,
    "worktree": "/srv/tidepool",
    "state": "dead",
    "outcome": None,
    "wave": "tidepool_w2",
    "task": "T3",
    "started_at": "2026-10-09T09:00:00Z",
    "arguments": NO_ARGUMENTS,
    "segments": [],
    "duration_ms": None,
    "cost_usd": None,
    "duration_partial": False,
    "cost_partial": False,
}
SECOND_LISTED = {
    "run": SECOND_RUN,
    "procedure": "deliver",
    "slot": "build",
    "role": "builder",
    "project": None,
    "worktree": "/srv/tidepool",
    "state": "finished",
    "outcome": "done",
    "wave": "tidepool_w2",
    "task": "T2",
    "started_at": "2026-10-08T09:00:00Z",
    "arguments": NO_ARGUMENTS,
    "segments": [{"segment": 1, "outcome": "done", "turns": 12, "duration_ms": 4200}],
    "duration_ms": 4200,
    "cost_usd": None,
    "duration_partial": False,
    "cost_partial": True,
}


class RunListTextTest(unittest.TestCase):
    def test_should_say_that_no_run_was_started(self):
        # Arrange
        document = {"schema_version": 1, "runs": []}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "no runs")

    def test_should_print_one_row_per_run_with_its_segments_its_measures_and_its_arguments_last(self):
        # Arrange
        document = {
            "schema_version": 1,
            "runs": [
                {
                    "run": FIRST_RUN,
                    "procedure": "deliver",
                    "slot": "build",
                    "role": "builder",
                    "project": None,
                    "wave": "tidepool_w1",
                    "task": "T1",
                    "state": "finished",
                    "outcome": "done",
                    "arguments": {"task": "@TASK.B82", "base": "integration/oak"},
                    "segments": [
                        {"segment": 1, "outcome": "wall_limit", "turns": 30, "duration_ms": 1500000},
                        {"segment": 2, "outcome": "done", "turns": 12, "duration_ms": 600000},
                    ],
                    "duration_ms": 2100000,
                    "cost_usd": 1.75,
                    "duration_partial": False,
                    "cost_partial": False,
                },
                {
                    "run": SECOND_RUN,
                    "procedure": "request-plan",
                    "slot": "plan",
                    "role": "planner",
                    "project": None,
                    "wave": None,
                    "task": None,
                    "state": "running",
                    "outcome": None,
                    "arguments": {"request": "add a cart"},
                    "segments": [
                        {"segment": 1, "outcome": "handed_over", "turns": 30, "duration_ms": 1500000},
                        {"segment": 2, "outcome": None, "turns": None, "duration_ms": None},
                    ],
                    "duration_ms": 1500000,
                    "cost_usd": None,
                    "duration_partial": True,
                    "cost_partial": True,
                },
            ],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "run                      procedure     slot   role     project  wave         task  state     outcome"
            "  segments             duration       cost      arguments\n"
            f"{FIRST_RUN}  deliver       build  builder  -        tidepool_w1  T1    finished  done   "
            "  wall_limit,done      0h35m          1.75 USD  base=integration/oak task=@TASK.B82\n"
            f"{SECOND_RUN}  request-plan  plan   planner  -        -            -     running   -      "
            "  handed_over,running  0h25m partial  -         request=add a cart",
        )

    def test_should_tell_two_runs_of_one_procedure_outside_a_wave_apart_by_their_arguments(self):
        # Arrange
        outside_a_wave = {
            "procedure": "awawa-task",
            "slot": "build",
            "role": "ada",
            "project": None,
            "wave": None,
            "task": None,
            "state": "finished",
            "outcome": "done",
            "duration_partial": False,
            "cost_partial": False,
        }
        document = {
            "schema_version": 1,
            "runs": [
                {
                    **outside_a_wave,
                    "run": FIRST_RUN,
                    "arguments": {"task": "@TASK.B71"},
                    "segments": [{"segment": 1, "outcome": "done", "turns": 20, "duration_ms": 720000}],
                    "duration_ms": 720000,
                    "cost_usd": 0.8,
                },
                {
                    **outside_a_wave,
                    "run": SECOND_RUN,
                    "arguments": {"task": "@TASK.B82"},
                    "segments": [
                        {"segment": 1, "outcome": "wall_limit", "turns": 30, "duration_ms": 1500000},
                        {"segment": 2, "outcome": "done", "turns": 12, "duration_ms": 600000},
                    ],
                    "duration_ms": 2100000,
                    "cost_usd": 1.75,
                },
            ],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "run                      procedure   slot   role  project  wave  task  state     outcome  segments"
            "         duration  cost      arguments\n"
            f"{FIRST_RUN}  awawa-task  build  ada   -        -     -     finished  done     done           "
            "  0h12m     0.80 USD  task=@TASK.B71\n"
            f"{SECOND_RUN}  awawa-task  build  ada   -        -     -     finished  done     wall_limit,done"
            "  0h35m     1.75 USD  task=@TASK.B82",
        )

    def test_should_print_a_dash_for_the_segments_the_measures_and_the_arguments_of_a_run_without_segment(self):
        # Arrange
        document = {
            "schema_version": 1,
            "runs": [
                {
                    "run": FIRST_RUN,
                    "procedure": "deliver",
                    "slot": "build",
                    "role": "builder",
                    "project": None,
                    "wave": None,
                    "task": None,
                    "state": "finished",
                    "outcome": "done",
                    "arguments": NO_ARGUMENTS,
                    "segments": [],
                    "duration_ms": None,
                    "cost_usd": None,
                    "duration_partial": False,
                    "cost_partial": False,
                }
            ],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "run                      procedure  slot   role     project  wave  task  state     outcome  segments"
            "  duration  cost  arguments\n"
            f"{FIRST_RUN}  deliver    build  builder  -        -     -     finished  done     -         -       "
            "  -     -",
        )


class RunListDiagnosticsTest(unittest.TestCase):
    def test_should_name_each_run_skipped_with_its_reason(self):
        # Arrange
        document = {"schema_version": 1, "runs": [], "skipped": [{"run": FIRST_RUN, "reason": "run.json is empty"}]}

        # Act
        diagnostics = COMMAND.describe_diagnostics(document)

        # Assert
        self.assertEqual(diagnostics, [f"skipped run {FIRST_RUN}: run.json is empty"])


class RunsListExitCodeTest(unittest.TestCase):
    def test_should_succeed(self):
        # Act
        exit_code = COMMAND.decide_exit_code({"schema_version": 1, "runs": [], "skipped": []})

        # Assert
        self.assertEqual(exit_code, 0)


class RunsListRequestTest(unittest.TestCase):
    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = Namespace(wave=None, task=None, state=None)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class RunsListSelectionTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        state_root = self.root / "state"
        write_run(
            state_root,
            create_run_record(FIRST_RUN, "tidepool_w1", "T1"),
            create_run_result(FIRST_RUN, "done", "2026-10-07T09:12:00Z"),
        )
        write_run(
            state_root,
            create_run_record(SECOND_RUN, "tidepool_w2", "T2"),
            create_run_result(SECOND_RUN, "done", "2026-10-08T09:12:00Z"),
        )
        write_run(state_root, create_run_record(THIRD_RUN, "tidepool_w2", "T3"), None)

    def test_should_keep_the_runs_of_the_wave_the_task_and_the_state_asked(self):
        # Arrange
        rows = [
            (
                "every run",
                Namespace(wave=ANY_WAVE, task=ANY_TASK, state=ANY_STATE),
                [FIRST_LISTED, SECOND_LISTED, DEAD_LISTED],
            ),
            (
                "the runs of a wave",
                Namespace(wave="tidepool_w2", task=ANY_TASK, state=ANY_STATE),
                [SECOND_LISTED, DEAD_LISTED],
            ),
            ("the runs of a task", Namespace(wave=ANY_WAVE, task="T1", state=ANY_STATE), [FIRST_LISTED]),
            ("a task of another wave", Namespace(wave="tidepool_w2", task="T1", state=ANY_STATE), []),
            ("the dead runs", Namespace(wave=ANY_WAVE, task=ANY_TASK, state="dead"), [DEAD_LISTED]),
            (
                "the finished runs of a wave",
                Namespace(wave="tidepool_w2", task=ANY_TASK, state="finished"),
                [SECOND_LISTED],
            ),
        ]
        for case, request, expected_runs in rows:
            with self.subTest(case=case):
                # Act
                document = COMMAND.run(request, create_test_runtime(create_test_paths(self.root)))

                # Assert
                self.assertEqual(document["runs"], expected_runs)
