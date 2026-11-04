import contextlib
import unittest

from brigade.errors import CommandFailed, ToolFailure
from brigade.system.remember_process_records import remember_process_records
from brigade.system.run_process import ProcessRecord, ProcessRequest
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

SHOW_TASK = ("awawa", "show", "@TASK.B1", "--json", "/cache/refs/shop/abc123")
FETCH_MAIN = ("git", "fetch", "--quiet", "origin", "main")
FETCHED_MAIN = ProcessRecord(argv=FETCH_MAIN, cwd="/srv/shop", exit_code=0, stdout="", stderr="", duration_ms=412)


class FailingTwiceThenAnsweringRunnerDouble:
    def __init__(self):
        self.outcomes = [
            ToolFailure("git fetch --quiet origin main timed out after 120 s"),
            CommandFailed(FETCH_MAIN, 128, "fatal: unable to access 'https://github.com/': Could not resolve host"),
            FETCHED_MAIN,
        ]
        self.requests = []

    def __call__(self, request: ProcessRequest) -> ProcessRecord:
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, ToolFailure):
            raise outcome
        return outcome


class RememberProcessRecordsOfARunThatRaisesTest(unittest.TestCase):
    def setUp(self):
        self.runner = FailingTwiceThenAnsweringRunnerDouble()
        self.run_process = remember_process_records(self.runner)
        self.request = ProcessRequest(argv=FETCH_MAIN, cwd="/srv/shop", timeout_s=120.0)

    def test_should_run_a_request_again_after_each_raise_until_it_answers(self):
        # Arrange
        with contextlib.suppress(ToolFailure):
            self.run_process(self.request)
        with contextlib.suppress(CommandFailed):
            self.run_process(self.request)

        # Act
        self.run_process(self.request)

        # Assert
        self.assertEqual(self.runner.requests, [self.request, self.request, self.request])

    def test_should_replay_the_answer_of_a_request_once_it_answered_after_raising(self):
        # Arrange
        with contextlib.suppress(ToolFailure):
            self.run_process(self.request)
        with contextlib.suppress(CommandFailed):
            self.run_process(self.request)
        self.run_process(self.request)

        # Act
        record = self.run_process(self.request)

        # Assert
        self.assertEqual(record, FETCHED_MAIN)


class RememberProcessRecordsTest(unittest.TestCase):
    def setUp(self):
        self.runner = RecordingProcessRunner({SHOW_TASK: ProcessAnswer(stdout='{"fields": []}')})
        self.run_process = remember_process_records(self.runner)
        self.request = ProcessRequest(argv=SHOW_TASK, cwd="/cache/refs/shop/abc123", timeout_s=300.0)

    def test_should_run_a_request_asked_twice_once(self):
        # Arrange
        self.run_process(self.request)

        # Act
        self.run_process(self.request)

        # Assert
        self.assertEqual(self.runner.list_argvs(), [SHOW_TASK])

    def test_should_answer_a_request_asked_again_with_the_record_of_its_first_run(self):
        # Arrange
        self.run_process(self.request)

        # Act
        record = self.run_process(self.request)

        # Assert
        self.assertEqual(
            record,
            ProcessRecord(
                argv=SHOW_TASK,
                cwd="/cache/refs/shop/abc123",
                exit_code=0,
                stdout='{"fields": []}',
                stderr="",
                duration_ms=0,
            ),
        )

    def test_should_run_each_request_differing_from_an_earlier_one_by_any_part(self):
        for differing in [
            ProcessRequest(argv=FETCH_MAIN, cwd="/srv/depot", timeout_s=120.0, environment={"GH_TOKEN": "build"}),
            ProcessRequest(argv=FETCH_MAIN, cwd="/srv/shop", timeout_s=60.0, environment={"GH_TOKEN": "build"}),
            ProcessRequest(
                argv=FETCH_MAIN,
                cwd="/srv/shop",
                timeout_s=120.0,
                acceptable_exit_codes=(0, 1),
                environment={"GH_TOKEN": "build"},
            ),
            ProcessRequest(
                argv=FETCH_MAIN, cwd="/srv/shop", timeout_s=120.0, stdin="main\n", environment={"GH_TOKEN": "build"}
            ),
            ProcessRequest(argv=FETCH_MAIN, cwd="/srv/shop", timeout_s=120.0, environment={"GH_TOKEN": "review"}),
        ]:
            with self.subTest(differing=differing):
                # Arrange
                first = ProcessRequest(
                    argv=FETCH_MAIN, cwd="/srv/shop", timeout_s=120.0, environment={"GH_TOKEN": "build"}
                )
                runner = RecordingProcessRunner()
                run_process = remember_process_records(runner)
                run_process(first)

                # Act
                run_process(differing)

                # Assert
                self.assertEqual(runner.requests, [first, differing])
