import contextlib
import functools
import io
import json
import os
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from brigade.commands.run_show import COMMAND
from brigade.errors import BrigadeError, UsageError
from brigade.runs.record_run_pid import record_run_pid
from brigade.system.resolve_plugin import PluginSources, resolve_plugin
from tests.awawa.provide_awawa import provide_awawa
from tests.create_process_runner import create_process_runner
from tests.unit.commands.run_directories import FIRST_RUN, create_run_record, create_run_result, write_run
from tests.unit.create_test_paths import create_test_paths
from tests.unit.create_test_runtime import create_test_runtime
from tests.unit.refuse_to_run import refuse_to_run

FINISHED_RUN = {
    "run": FIRST_RUN,
    "procedure": "deliver",
    "slot": "build",
    "role": "builder",
    "project": None,
    "worktree": "/srv/tidepool",
    "state": "finished",
    "outcome": "done",
    "wave": None,
    "task": None,
    "started_at": "2026-10-07T09:00:00Z",
    "message": "the task is delivered",
}
FOLLOWED_RUN = {
    "run": FIRST_RUN,
    "procedure": "deliver",
    "slot": "build",
    "role": "builder",
    "project": None,
    "worktree": "/srv/tidepool",
    "state": "finished",
    "outcome": "done",
    "wave": None,
    "task": None,
    "started_at": "2026-10-07T09:00:00Z",
}
FINISHED_SEGMENT = {
    "segment": 1,
    "outcome": "done",
    "turns": 12,
    "duration_ms": 4200,
    "started_at": "2026-10-07T09:11:55Z",
    "cost_usd": None,
}
NO_PROGRESS = None
NO_NOTES = []
NO_ARGUMENTS = {}
NO_EXECUTABLE_DIRECTORY = ""
MARKDOWN_PROGRESS = "- read the task\n- wrote the tests\n"
AWAWA_PROGRESS = (
    "SCHEMA ENTRY\n"
    '\tDESC "a step the run completed"\n'
    "\tFIELD DONE string\n"
    "\t\tREQUIRED\n"
    '\t\tDESC "what the step did, one line"\n'
    "\n"
    "ENTRY e1\n"
    '\tDONE "read the task"\n'
)
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
            "segments": [{"segment": 1, "outcome": None, "turns": None, "duration_ms": None}],
            "notes": NO_NOTES,
            "progress": NO_PROGRESS,
            "log": None,
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
            "segment  outcome  turns  duration\n"
            "1        -        -      -",
        )

    def test_should_add_the_log_after_the_segments(self):
        # Arrange
        document = {
            "schema_version": 1,
            "run": FINISHED_RUN,
            "segments": [FINISHED_SEGMENT],
            "notes": NO_NOTES,
            "progress": NO_PROGRESS,
            "log": [{"at": "2026-10-07T09:01:00Z", "segment": 1, "kind": "text", "summary": "reads the task"}],
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
            "segment  outcome  turns  duration\n"
            "1        done     12     0m04s\n"
            "\n"
            "2026-10-07T09:01:00Z  1  text  reads the task",
        )

    def test_should_print_the_progress_after_the_segments_and_before_the_log(self):
        # Arrange
        document = {
            "schema_version": 1,
            "run": FINISHED_RUN,
            "segments": [FINISHED_SEGMENT],
            "notes": NO_NOTES,
            "progress": {"text": "ENTRY e1\n  DONE: read the task\n", "entities": None},
            "log": [{"at": "2026-10-07T09:01:00Z", "segment": 1, "kind": "text", "summary": "reads the task"}],
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
            "segment  outcome  turns  duration\n"
            "1        done     12     0m04s\n"
            "\n"
            "ENTRY e1\n"
            "  DONE: read the task\n"
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

    def test_should_print_the_notes_with_the_segment_that_carried_each_after_the_segments(self):
        # Arrange
        document = {
            "schema_version": 1,
            "run": FINISHED_RUN,
            "segments": [FINISHED_SEGMENT],
            "notes": [
                {"at": "2026-10-07T09:02:00Z", "text": "rebase onto main before the check", "segment": 2},
                {"at": "2026-10-07T09:05:00Z", "text": "the corpus of main holds two L016 errors", "segment": None},
            ],
            "progress": {"text": "ENTRY e1\n  DONE: read the task\n", "entities": None},
            "log": None,
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
            "segment  outcome  turns  duration\n"
            "1        done     12     0m04s\n"
            "\n"
            "noted                 carried by  note\n"
            "2026-10-07T09:02:00Z  segment 2   rebase onto main before the check\n"
            "2026-10-07T09:05:00Z  pending     the corpus of main holds two L016 errors\n"
            "\n"
            "ENTRY e1\n"
            "  DONE: read the task",
        )


class RunsShowExitCodeTest(unittest.TestCase):
    def test_should_exit_on_the_outcome_of_a_run_followed_to_its_end(self):
        # Arrange
        rows = [
            ("a run shown", {"run": {**FINISHED_RUN, "outcome": "failed"}, "segments": [], "log": None}, 0),
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
JOURNAL_POLLED_AT_ONCE = "log_poll_s = 0.01\n"


class RunsShowFollowingARunningRunTest(unittest.TestCase):
    def test_should_print_the_records_until_the_run_ends(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        run_directory = write_run(root / "state", create_run_record(FIRST_RUN, None, None), None)
        record_run_pid(run_directory, os.getpid())
        (run_directory / "log.jsonl").write_text(json.dumps(JOURNAL_RECORD) + "\n", encoding="utf-8")
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
            "segment  outcome  turns  duration\n"
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
    def test_should_read_the_run_again_every_log_poll_s_seconds_of_the_configuration(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write_run(root / "state", create_run_record(FIRST_RUN, None, None), None)
        polls = PollOnceDouble()
        runtime = create_test_runtime(create_test_paths(root), poll_until_signalled=polls.poll_until_signalled)
        runtime.paths.config_root.mkdir(parents=True)
        runtime.paths.configuration_file.write_text("log_poll_s = 3600\n", encoding="utf-8")

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
        (run_directory / "log.jsonl").write_text(json.dumps(JOURNAL_RECORD) + "\n", encoding="utf-8")

    def test_should_show_the_run_with_its_log(self):
        # Arrange
        request = Namespace(run=FIRST_RUN, log=True, follow=False)

        # Act
        document = COMMAND.run(request, create_test_runtime(create_test_paths(self.root)))

        # Assert
        self.assertEqual(
            document,
            {
                "schema_version": 1,
                "run": FINISHED_RUN,
                "arguments": NO_ARGUMENTS,
                "segments": [FINISHED_SEGMENT],
                "notes": NO_NOTES,
                "progress": NO_PROGRESS,
                "log": [JOURNAL_RECORD],
            },
        )

    def test_should_print_the_run_and_its_log_when_following_a_run_already_ended(self):
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
            "segment  outcome  turns  duration\n"
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


class RunsShowOfARunWithItsProgressTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.run_directory = write_run(
            self.root / "state",
            create_run_record(FIRST_RUN, None, None),
            create_run_result(FIRST_RUN, "done", "2026-10-07T09:12:00Z"),
        )
        sources = PluginSources(executable_search_path=NO_EXECUTABLE_DIRECTORY, run_process=refuse_to_run)
        self.resolve_plugin = functools.partial(resolve_plugin, sources=sources)

    def test_should_carry_the_text_of_a_markdown_progress_with_no_entities(self):
        # Arrange
        (self.run_directory / "progress.md").write_text(MARKDOWN_PROGRESS, encoding="utf-8")
        runtime = create_test_runtime(create_test_paths(self.root), resolve_plugin=self.resolve_plugin)

        # Act
        document = COMMAND.run(Namespace(run=FIRST_RUN, log=False, follow=False), runtime)

        # Assert
        self.assertEqual(document["progress"], {"text": "- read the task\n- wrote the tests\n", "entities": None})

    def test_should_carry_no_progress_for_a_progress_holding_no_entry(self):
        # Arrange
        (self.run_directory / "progress.md").write_text("", encoding="utf-8")
        runtime = create_test_runtime(create_test_paths(self.root), resolve_plugin=self.resolve_plugin)

        # Act
        document = COMMAND.run(Namespace(run=FIRST_RUN, log=False, follow=False), runtime)

        # Assert
        self.assertIsNone(document["progress"])

    def test_should_render_an_awawa_progress_whatever_form_the_configuration_names_now(self):
        # Arrange
        (self.run_directory / "progress.awawa").write_text(AWAWA_PROGRESS, encoding="utf-8")
        runtime = create_test_runtime(
            create_test_paths(self.root),
            run_process=create_process_runner(provide_awawa(self)),
            resolve_plugin=self.resolve_plugin,
        )
        runtime.paths.config_root.mkdir(parents=True)
        runtime.paths.configuration_file.write_text('progress_form = "markdown"\n', encoding="utf-8")

        # Act
        document = COMMAND.run(Namespace(run=FIRST_RUN, log=False, follow=False), runtime)

        # Assert
        self.assertEqual(
            document["progress"],
            {
                "text": "ENTRY e1\n  DONE: read the task\n",
                "entities": [{"type": "ENTRY", "name": "e1", "fields": [{"name": "DONE", "value": "read the task"}]}],
            },
        )

    def test_should_print_no_progress_when_following_the_run(self):
        # Arrange
        (self.run_directory / "progress.md").write_text(MARKDOWN_PROGRESS, encoding="utf-8")
        printed = io.StringIO()

        # Act
        with contextlib.redirect_stdout(printed):
            COMMAND.run(
                Namespace(run=FIRST_RUN, log=False, follow=True), create_test_runtime(create_test_paths(self.root))
            )

        # Assert
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
            "segment  outcome  turns  duration\n"
            "1        done     12     0m04s\n"
            "\n",
        )


class RunsShowOfANotedRunTest(unittest.TestCase):
    def test_should_list_the_notes_delivered_with_their_segment_and_the_notes_pending(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        run_directory = write_run(
            root / "state",
            create_run_record(FIRST_RUN, None, None),
            create_run_result(FIRST_RUN, "done", "2026-10-07T09:12:00Z"),
        )
        (run_directory / "segments" / "1" / "notes.json").write_text('{"carried": 0}\n', encoding="utf-8")
        (run_directory / "segments" / "2").mkdir()
        (run_directory / "segments" / "2" / "notes.json").write_text('{"carried": 1}\n', encoding="utf-8")
        (run_directory / "notes.jsonl").write_text(
            '{"at": "2026-10-07T09:02:00Z", "text": "rebase onto main before the check"}\n'
            '{"at": "2026-10-07T09:05:00Z", "text": "the corpus of main holds two L016 errors"}\n',
            encoding="utf-8",
        )

        # Act
        document = COMMAND.run(
            Namespace(run=FIRST_RUN, log=False, follow=False), create_test_runtime(create_test_paths(root))
        )

        # Assert
        self.assertEqual(
            document["notes"],
            [
                {"at": "2026-10-07T09:02:00Z", "text": "rebase onto main before the check", "segment": 2},
                {"at": "2026-10-07T09:05:00Z", "text": "the corpus of main holds two L016 errors", "segment": None},
            ],
        )

    def test_should_name_the_segments_that_carried_the_notes_in_the_order_of_their_numbers(self):
        # Arrange
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        run_directory = write_run(
            root / "state",
            create_run_record(FIRST_RUN, None, None),
            create_run_result(FIRST_RUN, "done", "2026-10-07T09:12:00Z"),
        )
        (run_directory / "segments" / "9").mkdir()
        (run_directory / "segments" / "9" / "notes.json").write_text('{"carried": 1}\n', encoding="utf-8")
        (run_directory / "segments" / "10").mkdir()
        (run_directory / "segments" / "10" / "notes.json").write_text('{"carried": 1}\n', encoding="utf-8")
        (run_directory / "notes.jsonl").write_text(
            '{"at": "2026-10-07T09:02:00Z", "text": "rebase onto main before the check"}\n'
            '{"at": "2026-10-07T09:05:00Z", "text": "the corpus of main holds two L016 errors"}\n',
            encoding="utf-8",
        )

        # Act
        document = COMMAND.run(
            Namespace(run=FIRST_RUN, log=False, follow=False), create_test_runtime(create_test_paths(root))
        )

        # Assert
        self.assertEqual(
            document["notes"],
            [
                {"at": "2026-10-07T09:02:00Z", "text": "rebase onto main before the check", "segment": 9},
                {"at": "2026-10-07T09:05:00Z", "text": "the corpus of main holds two L016 errors", "segment": 10},
            ],
        )
