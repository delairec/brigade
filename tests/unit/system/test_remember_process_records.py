import unittest

from brigade.system.remember_process_records import remember_process_records
from brigade.system.run_process import ProcessRecord, ProcessRequest
from tests.unit.recording_process_runner import ProcessAnswer, RecordingProcessRunner

SHOW_TASK = ("awawa", "show", "@TASK.B1", "--json", "/cache/refs/shop/abc123")
FETCH_MAIN = ("git", "fetch", "--quiet", "origin", "main")


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
