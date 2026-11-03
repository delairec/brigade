import json
import os
import tempfile
import unittest
from pathlib import Path

from tests.awawa.provide_awawa_from import provide_awawa_from
from tests.process_launcher import ProcessLauncher

SCRIPTED_AWAWA_DIRECTORY = Path(__file__).resolve().parent / "fixtures" / "scripted-awawa"
RECORDING_ASKED = "1"
FMT_RECORDING = {
    "version": "awawa 2.7.0",
    "call": {
        "arguments": ["fmt", "<tmp:0>/corpus/tasks.awawa"],
        "cwd": "<tmp:0>",
        "directories": [],
        "inputs": {"<tmp:0>/corpus/tasks.awawa": "TASK  B1\n"},
    },
    "outcome": {"stdout": "the recorded answer\n", "stderr": "", "exit_code": 0, "rewritten": {}},
}


class ProvideAwawaWhileRecordingTest(unittest.TestCase):
    def setUp(self):
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        self.root = Path(root.name)
        self.corpus = self.root / "corpus"
        self.corpus.mkdir()
        self.environment = {
            "PATH": f"{SCRIPTED_AWAWA_DIRECTORY}{os.pathsep}{os.environ['PATH']}",
            "AWAWA_RECORD": RECORDING_ASKED,
        }

    def test_should_have_the_real_awawa_answer_while_the_recordings_are_renewed(self):
        # Arrange
        search_path = provide_awawa_from(self, self.environment, self.root / "recordings")
        (self.corpus / "tasks.awawa").write_text("TASK  B1\n")

        # Act
        completed = ProcessLauncher.run(
            ["awawa", "fmt", str(self.corpus / "tasks.awawa")],
            cwd=self.root,
            env={**os.environ, "PATH": search_path},
            capture_output=True,
            text=True,
            check=False,
        )

        # Assert
        self.assertEqual(
            [completed.stdout, completed.stderr, completed.returncode],
            [f"{self.corpus}/tasks.awawa\n", "1 file rewritten\n", 0],
        )


class ProvideAwawaOnThePathTest(unittest.TestCase):
    def setUp(self):
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        self.root = Path(root.name)
        self.corpus = self.root / "corpus"
        self.corpus.mkdir()
        self.recordings = self.root / "recordings"
        self.recordings.mkdir()
        self.environment = {"PATH": f"{SCRIPTED_AWAWA_DIRECTORY}{os.pathsep}{os.environ['PATH']}"}

    def run_awawa_on(self, search_path: str, *arguments: str):
        return ProcessLauncher.run(
            ["awawa", *arguments],
            cwd=self.root,
            env={**os.environ, "PATH": search_path},
            capture_output=True,
            text=True,
            check=False,
        )

    def run_inner_case(self, *arguments: str) -> list:
        environment = self.environment
        recordings = self.recordings
        run_awawa_on = self.run_awawa_on

        class CallingAwawaTest(unittest.TestCase):
            def test_call(self):
                # Arrange
                search_path = provide_awawa_from(self, environment, recordings)

                # Act
                run_awawa_on(search_path, *arguments)

        result = unittest.TestResult()
        CallingAwawaTest("test_call").run(result)
        return result.failures

    def test_should_fail_the_test_of_a_call_never_recorded_saying_how_to_record_it(self):
        # Arrange
        (self.corpus / "tasks.awawa").write_text("TASK  B1\n")

        # Act
        failures = self.run_inner_case("fmt", str(self.corpus / "tasks.awawa"))

        # Assert
        [(_, failure)] = failures
        self.assertIn(
            f"awawa has no recording of: awawa fmt {self.corpus}/tasks.awawa\n"
            "record the calls with awawa on PATH: AWAWA_RECORD=1 python3 -m unittest"
            " tests.awawa.test_provide_awawa.ProvideAwawaOnThePathTest.run_inner_case.<locals>.CallingAwawaTest.test_call",
            failure,
        )

    def test_should_have_the_real_awawa_answer_a_recorded_call(self):
        # Arrange
        search_path = provide_awawa_from(self, self.environment, self.recordings)
        (self.recordings / "fmt.json").write_text(json.dumps(FMT_RECORDING))
        (self.corpus / "tasks.awawa").write_text("TASK  B1\n")

        # Act
        completed = self.run_awawa_on(search_path, "fmt", str(self.corpus / "tasks.awawa"))

        # Assert
        self.assertEqual(
            [completed.stdout, completed.stderr, completed.returncode],
            [f"{self.corpus}/tasks.awawa\n", "1 file rewritten\n", 0],
        )
