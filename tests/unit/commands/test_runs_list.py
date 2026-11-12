import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.runs_list import COMMAND
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
}


class RunsListTextTest(unittest.TestCase):
    def test_should_say_that_no_run_was_started(self):
        # Arrange
        document = {"schema_version": 1, "runs": []}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "no runs")

    def test_should_print_one_row_per_run_naming_its_wave_and_its_task_and_marking_what_is_absent(self):
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
                    "state": "dead",
                    "outcome": None,
                },
                {
                    "run": SECOND_RUN,
                    "procedure": "wave-plan",
                    "slot": "plan",
                    "role": "planner",
                    "project": None,
                    "wave": None,
                    "task": None,
                    "state": "running",
                    "outcome": None,
                },
            ],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            "run                      procedure  slot   role     project  wave         task  state    outcome\n"
            f"{FIRST_RUN}  deliver    build  builder  -        tidepool_w1  T1    dead     -\n"
            f"{SECOND_RUN}  wave-plan  plan   planner  -        -            -     running  -",
        )


class RunsListDiagnosticsTest(unittest.TestCase):
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
