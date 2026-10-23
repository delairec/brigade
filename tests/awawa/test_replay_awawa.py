import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.awawa.install_fake_awawa import install_fake_awawa
from tests.process_launcher import ProcessLauncher

SCRIPTED_AWAWA = Path(__file__).resolve().parent / "fixtures" / "scripted-awawa" / "awawa"
NO_REAL_AWAWA = None
LINT_RECORDING = {
    "version": "awawa 2.7.0",
    "call": {
        "arguments": ["lint", "--strict", "<tmp:0>/corpus"],
        "cwd": "<tmp:0>",
        "directories": ["<tmp:0>/corpus"],
        "inputs": {"<tmp:0>/corpus/tasks.awawa": "TASK B1\n"},
    },
    "outcome": {
        "stdout": "<tmp:0>/corpus/tasks.awawa:1:1 L016 TASK B1 lacks its TITLE\n",
        "stderr": "1 error\n",
        "exit_code": 1,
        "rewritten": {},
    },
}
UNREADABLE_INPUT_RECORDING = {
    "version": "awawa 2.7.0",
    "call": {
        "arguments": ["lint", "--strict", "<tmp:0>/corpus"],
        "cwd": "<tmp:0>",
        "directories": ["<tmp:0>/corpus"],
        "inputs": {"<tmp:0>/corpus/tasks.awawa": None},
    },
    "outcome": {"stdout": "", "stderr": "Permission denied (os error 13)\n", "exit_code": 2, "rewritten": {}},
}
FMT_RECORDING = {
    "version": "awawa 2.7.0",
    "call": {
        "arguments": ["fmt", "<tmp:0>/corpus/tasks.awawa"],
        "cwd": "<tmp:0>",
        "directories": [],
        "inputs": {"<tmp:0>/corpus/tasks.awawa": "TASK  B1\n"},
    },
    "outcome": {
        "stdout": "",
        "stderr": "",
        "exit_code": 0,
        "rewritten": {"<tmp:0>/corpus/tasks.awawa": "TASK B1\n"},
    },
}


class FakeAwawaTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.recordings = Path(self.root.name) / "recordings"
        self.recordings.mkdir()
        self.corpus = Path(self.root.name) / "corpus"
        self.corpus.mkdir()

    def tearDown(self):
        self.root.cleanup()

    def record(self, recording: dict) -> None:
        (self.recordings / "recording.json").write_text(json.dumps(recording))

    def run_awawa(self, *arguments: str) -> subprocess.CompletedProcess:
        return self.run_awawa_on(self.search_path, *arguments)

    def run_awawa_on(self, search_path: str, *arguments: str) -> subprocess.CompletedProcess:
        return ProcessLauncher.run(
            ["awawa", *arguments],
            cwd=self.root.name,
            env={**os.environ, "PATH": search_path},
            capture_output=True,
            text=True,
            check=False,
        )

    def run_inner_case(self, *arguments: str) -> str:
        recordings = self.recordings
        run_awawa_on = self.run_awawa_on

        class CallingAwawaTest(unittest.TestCase):
            def test_call(self):
                # Arrange
                search_path = install_fake_awawa(self, recordings, NO_REAL_AWAWA, os.environ["PATH"])

                # Act
                run_awawa_on(search_path, *arguments)

        result = unittest.TestResult()
        CallingAwawaTest("test_call").run(result)
        return "".join(trace for _, trace in result.failures)


class FakeAwawaReplayTest(FakeAwawaTestCase):
    def test_should_answer_a_recorded_call_with_its_outputs_on_the_paths_of_the_test(self):
        # Arrange
        self.search_path = install_fake_awawa(self, self.recordings, NO_REAL_AWAWA, os.environ["PATH"])
        self.record(LINT_RECORDING)
        (self.corpus / "tasks.awawa").write_text("TASK B1\n")

        # Act
        completed = self.run_awawa("lint", "--strict", str(self.corpus))

        # Assert
        self.assertEqual(
            [completed.stdout, completed.stderr, completed.returncode],
            [f"{self.corpus}/tasks.awawa:1:1 L016 TASK B1 lacks its TITLE\n", "1 error\n", 1],
        )

    def test_should_rewrite_the_files_the_recorded_call_rewrote(self):
        # Arrange
        self.search_path = install_fake_awawa(self, self.recordings, NO_REAL_AWAWA, os.environ["PATH"])
        self.record(FMT_RECORDING)
        (self.corpus / "tasks.awawa").write_text("TASK  B1\n")

        # Act
        self.run_awawa("fmt", str(self.corpus / "tasks.awawa"))

        # Assert
        self.assertEqual((self.corpus / "tasks.awawa").read_text(), "TASK B1\n")

    def test_should_answer_a_call_on_an_unreadable_input_file_recorded_as_null(self):
        # Arrange
        self.search_path = install_fake_awawa(self, self.recordings, NO_REAL_AWAWA, os.environ["PATH"])
        self.record(UNREADABLE_INPUT_RECORDING)
        unreadable = self.corpus / "tasks.awawa"
        unreadable.write_text("TASK B1\n")
        unreadable.chmod(0)

        # Act
        completed = self.run_awawa("lint", "--strict", str(self.corpus))

        # Assert
        self.assertEqual([completed.stderr, completed.returncode], ["Permission denied (os error 13)\n", 2])


class FakeAwawaWithoutARecordingTest(FakeAwawaTestCase):
    def test_should_fail_the_test_naming_the_arguments_of_a_call_never_recorded(self):
        # Act
        failures = self.run_inner_case("show", "@AGENT.ghost", "--json", str(self.corpus))

        # Assert
        self.assertIn(f"awawa has no recording of: awawa show @AGENT.ghost --json {self.corpus}", failures)

    def test_should_fail_the_test_of_a_call_whose_input_files_differ_from_the_recording(self):
        # Arrange
        self.record(LINT_RECORDING)
        (self.corpus / "tasks.awawa").write_text("TASK B2\n")

        # Act
        failures = self.run_inner_case("lint", "--strict", str(self.corpus))

        # Assert
        self.assertIn(f"awawa has no recording of: awawa lint --strict {self.corpus}", failures)


class FakeAwawaRecordingTest(FakeAwawaTestCase):
    def test_should_record_what_the_real_awawa_answered_and_rewrote(self):
        # Arrange
        self.search_path = install_fake_awawa(self, self.recordings, str(SCRIPTED_AWAWA), os.environ["PATH"])
        (self.corpus / "tasks.awawa").write_text("TASK  B1\n")

        # Act
        self.run_awawa("fmt", str(self.corpus / "tasks.awawa"))

        # Assert
        self.assertEqual(
            json.loads(next(self.recordings.iterdir()).read_text()),
            {
                "version": "awawa 2.7.0",
                "call": {
                    "arguments": ["fmt", "<tmp:0>/corpus/tasks.awawa"],
                    "cwd": "<tmp:0>",
                    "directories": [],
                    "inputs": {"<tmp:0>/corpus/tasks.awawa": "TASK  B1\n"},
                },
                "run_order": [],
                "outcome": {
                    "stdout": "<tmp:0>/corpus/tasks.awawa\n",
                    "stderr": "1 file rewritten\n",
                    "exit_code": 0,
                    "rewritten": {"<tmp:0>/corpus/tasks.awawa": "TASK B1\n"},
                },
            },
        )

    def test_should_record_the_run_ids_of_the_call_in_the_order_they_sort(self):
        # Arrange
        self.search_path = install_fake_awawa(self, self.recordings, str(SCRIPTED_AWAWA), os.environ["PATH"])
        (self.corpus / "answers.awawa").write_text(
            "ANSWER trees_20261015T124950Z_f00000\nANSWER trees_20261015T124950Z_05a3de\n"
        )

        # Act
        self.run_awawa("fmt", str(self.corpus / "answers.awawa"))

        # Assert
        self.assertEqual(
            json.loads(next(self.recordings.iterdir()).read_text())["run_order"], ["<run_name:2>", "<run_name:1>"]
        )

    def test_should_answer_the_call_with_what_the_real_awawa_answered(self):
        # Arrange
        self.search_path = install_fake_awawa(self, self.recordings, str(SCRIPTED_AWAWA), os.environ["PATH"])
        (self.corpus / "tasks.awawa").write_text("TASK  B1\n")

        # Act
        completed = self.run_awawa("fmt", str(self.corpus / "tasks.awawa"))

        # Assert
        self.assertEqual(
            [completed.stdout, completed.stderr, completed.returncode],
            [f"{self.corpus}/tasks.awawa\n", "1 file rewritten\n", 0],
        )
