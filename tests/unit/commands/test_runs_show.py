import contextlib
import io
import json
import os
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.runs_show import COMMAND
from brigade.errors import BrigadeError, UsageError
from brigade.runs.record_run_pid import record_run_pid
from tests.unit.commands.run_directories import FIRST_RUN, create_run_record, create_run_result, write_run
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime

FINISHED_RUN = {
    "run": FIRST_RUN,
    "procedure": "deliver",
    "slot": "build",
    "role": "builder",
    "project": None,
    "worktree": "/home/user/tidepool",
    "state": "finished",
    "outcome": "done",
    "wave": None,
    "task": None,
    "message": "the task is delivered",
}
FOLLOWED_RUN = {
    "run": FIRST_RUN,
    "procedure": "deliver",
    "slot": "build",
    "role": "builder",
    "project": None,
    "worktree": "/home/user/tidepool",
    "state": "finished",
    "outcome": "done",
    "wave": None,
    "task": None,
}
FINISHED_SEGMENT = {"segment": 1, "outcome": "done", "steps": 12, "duration_ms": 4200}
JOURNAL_RECORD = {
    "schema_version": 1,
    "at": "2026-10-07T09:01:00Z",
    "segment": 1,
    "kind": "text",
    "summary": "reads the task",
    "cut": False,
}


class RunsShowTextTest(unittest.TestCase):
    def test_should_print_the_summary_and_the_segments_of_a_run(self):
        # Arrange
        document = {
            "schema_version": 1,
            "run": {**FINISHED_RUN, "project": None, "outcome": None, "message": None},
            "segments": [{"segment": 1, "outcome": None, "steps": None, "duration_ms": None}],
            "journal": None,
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            f"run        {FIRST_RUN}\n"
            "procedure  deliver\n"
            "slot       build\n"
            "role       builder\n"
            "project    -\n"
            "state      finished\n"
            "outcome    -\n"
            "message    -\n"
            "\n"
            "segment  outcome  steps  duration\n"
            "1        -        -      -",
        )

    def test_should_add_the_journal_after_the_segments(self):
        # Arrange
        document = {
            "schema_version": 1,
            "run": FINISHED_RUN,
            "segments": [FINISHED_SEGMENT],
            "journal": [{"at": "2026-10-07T09:01:00Z", "segment": 1, "kind": "text", "summary": "reads the task"}],
        }

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(
            text,
            f"run        {FIRST_RUN}\n"
            "procedure  deliver\n"
            "slot       build\n"
            "role       builder\n"
            "project    -\n"
            "state      finished\n"
            "outcome    done\n"
            "message    the task is delivered\n"
            "\n"
            "segment  outcome  steps  duration\n"
            "1        done     12     0m04s\n"
            "\n"
            "2026-10-07T09:01:00Z  1  text  reads the task",
        )

    def test_should_end_a_followed_run_on_its_state_and_outcome(self):
        # Arrange
        document = {"schema_version": 1, "run": FINISHED_RUN, "interrupted": False}

        # Act
        text = COMMAND.render_text(document)

        # Assert
        self.assertEqual(text, "\nstate      finished\noutcome    done")


class RunsShowExitCodeTest(unittest.TestCase):
    def test_should_exit_on_the_outcome_of_a_run_followed_to_its_end(self):
        # Arrange
        rows = [
            ("a run shown", {"run": {**FINISHED_RUN, "outcome": "failed"}, "segments": [], "journal": None}, 0),
            ("a run followed until a signal", {"run": {**FINISHED_RUN, "outcome": "failed"}, "interrupted": True}, 0),
            ("a run followed to its failure", {"run": {**FINISHED_RUN, "outcome": "failed"}, "interrupted": False}, 1),
            ("a run followed to its end", {"run": FINISHED_RUN, "interrupted": False}, 0),
            (
                "a run followed to no outcome declared",
                {"run": {**FINISHED_RUN, "outcome": "undeclared"}, "interrupted": False},
                3,
            ),
            (
                "a run followed to its block",
                {"run": {**FINISHED_RUN, "outcome": "blocked"}, "interrupted": False},
                10,
            ),
            (
                "a run followed to its turn limit",
                {"run": {**FINISHED_RUN, "outcome": "turn_limit"}, "interrupted": False},
                12,
            ),
            (
                "a run followed to its soft limit",
                {"run": {**FINISHED_RUN, "outcome": "soft_limit"}, "interrupted": False},
                13,
            ),
        ]
        for case, document, expected_exit_code in rows:
            with self.subTest(case=case):
                # Act
                exit_code = COMMAND.decide_exit_code(document)

                # Assert
                self.assertEqual(exit_code, expected_exit_code)


class RunsShowRequestTest(unittest.TestCase):
    def test_should_refuse_to_follow_a_run_in_json(self):
        # Arrange
        options = Namespace(run=FIRST_RUN, log=False, follow=True, json=True)

        # Act
        with self.assertRaises(UsageError) as raised:
            COMMAND.read_request(options)

        # Assert
        self.assertEqual(str(raised.exception), "--follow and --json exclude each other")

    def test_should_take_the_options_as_the_request(self):
        # Arrange
        options = Namespace(run=FIRST_RUN, log=False, follow=True, json=False)

        # Act
        request = COMMAND.read_request(options)

        # Assert
        self.assertIs(request, options)


class RunFinishingOnItsFirstRecordStdoutDouble(io.StringIO):
    def __init__(self, run_directory: Path):
        super().__init__()
        self.run_directory = run_directory

    def write(self, text: str) -> int:
        if JOURNAL_LINE in text:
            (self.run_directory / "result.json").write_text(
                json.dumps(create_run_result(FIRST_RUN, "done", "2026-10-07T09:12:00Z")), encoding="utf-8"
            )
        return super().write(text)


JOURNAL_LINE = "2026-10-07T09:01:00Z  1  text  reads the task\n"
JOURNAL_POLLED_AT_ONCE = "journal_poll_s = 0.01\n"


class RunsShowFollowingARunningRunTest(unittest.TestCase):
    def test_should_print_the_records_until_the_run_ends(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        run_directory = write_run(root / "state", create_run_record(FIRST_RUN, None, None), None)
        record_run_pid(run_directory, os.getpid())
        (run_directory / "journal.jsonl").write_text(json.dumps(JOURNAL_RECORD) + "\n", encoding="utf-8")
        printed = RunFinishingOnItsFirstRecordStdoutDouble(run_directory)
        runtime = create_test_runtime(create_test_paths(root))
        runtime.paths.config_root.mkdir(parents=True)
        runtime.paths.configuration_file.write_text(JOURNAL_POLLED_AT_ONCE, encoding="utf-8")

        # Act
        with contextlib.redirect_stdout(printed):
            document = COMMAND.run(Namespace(run=FIRST_RUN, log=False, follow=True), runtime)

        # Assert
        self.assertEqual(document, {"schema_version": 1, "run": FOLLOWED_RUN, "interrupted": False})
        self.assertEqual(
            printed.getvalue(),
            f"run        {FIRST_RUN}\n"
            "procedure  deliver\n"
            "slot       build\n"
            "role       builder\n"
            "project    -\n"
            "state      running\n"
            "outcome    -\n"
            "message    -\n"
            "\n"
            "segment  outcome  steps  duration\n"
            "\n"
            f"{JOURNAL_LINE}",
        )


class PollOnceDouble:
    def __init__(self):
        self.intervals_s = []

    def poll_until_signalled(self, poll, interval_s: float) -> bool:
        self.intervals_s.append(interval_s)
        poll()
        return False


class RunsShowFollowIntervalTest(unittest.TestCase):
    def test_should_read_the_run_again_every_journal_poll_s_seconds_of_the_configuration(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_run(root / "state", create_run_record(FIRST_RUN, None, None), None)
        polls = PollOnceDouble()
        runtime = create_test_runtime(create_test_paths(root), poll_until_signalled=polls.poll_until_signalled)
        runtime.paths.config_root.mkdir(parents=True)
        runtime.paths.configuration_file.write_text("journal_poll_s = 3600\n", encoding="utf-8")

        # Act
        with contextlib.redirect_stdout(io.StringIO()):
            COMMAND.run(Namespace(run=FIRST_RUN, log=False, follow=True), runtime)

        # Assert
        self.assertEqual(polls.intervals_s, [3600])


class RunsShowOfAFinishedRunTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        run_directory = write_run(
            self.root / "state",
            create_run_record(FIRST_RUN, None, None),
            create_run_result(FIRST_RUN, "done", "2026-10-07T09:12:00Z"),
        )
        (run_directory / "journal.jsonl").write_text(json.dumps(JOURNAL_RECORD) + "\n", encoding="utf-8")

    def test_should_show_the_run_with_its_journal(self):
        # Arrange
        request = Namespace(run=FIRST_RUN, log=True, follow=False)

        # Act
        document = COMMAND.run(request, create_test_runtime(create_test_paths(self.root)))

        # Assert
        self.assertEqual(
            document,
            {"schema_version": 1, "run": FINISHED_RUN, "segments": [FINISHED_SEGMENT], "journal": [JOURNAL_RECORD]},
        )

    def test_should_print_the_run_and_its_journal_when_following_a_run_already_ended(self):
        # Arrange
        request = Namespace(run=FIRST_RUN, log=False, follow=True)
        printed = io.StringIO()

        # Act
        with contextlib.redirect_stdout(printed):
            document = COMMAND.run(request, create_test_runtime(create_test_paths(self.root)))

        # Assert
        self.assertEqual(document, {"schema_version": 1, "run": FOLLOWED_RUN, "interrupted": False})
        self.assertEqual(
            printed.getvalue(),
            f"run        {FIRST_RUN}\n"
            "procedure  deliver\n"
            "slot       build\n"
            "role       builder\n"
            "project    -\n"
            "state      finished\n"
            "outcome    done\n"
            "message    the task is delivered\n"
            "\n"
            "segment  outcome  steps  duration\n"
            "1        done     12     0m04s\n"
            "\n"
            "2026-10-07T09:01:00Z  1  text  reads the task\n",
        )

    def test_should_refuse_a_run_never_started(self):
        # Arrange
        request = Namespace(run="20261009T090000Z-d90c03", log=False, follow=False)

        # Act
        with self.assertRaises(BrigadeError) as raised:
            COMMAND.run(request, create_test_runtime(create_test_paths(self.root)))

        # Assert
        self.assertEqual(str(raised.exception), "no run 20261009T090000Z-d90c03")
