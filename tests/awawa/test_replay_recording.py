import os
import unittest
from pathlib import Path
from unittest import mock

from tests.awawa.replay_recording import replay_recording

SORTING_AWAWA = Path(__file__).resolve().parent / "fixtures" / "sorting-awawa"
RECORDING_OF_TWO_RUNS_OF_ONE_SECOND = {
    "version": "awawa 2.7.0",
    "call": {
        "arguments": ["status", "<tmp:0>"],
        "cwd": "<tmp:0>",
        "directories": ["<tmp:0>"],
        "inputs": {"<tmp:0>/answers.awawa": "ANSWER trees_<run_name:1>\nANSWER trees_<run_name:2>\n"},
    },
    "run_order": ["<run_name:2>", "<run_name:1>"],
    "outcome": {
        "stdout": "ANSWER trees_<run_name:2>\nANSWER trees_<run_name:1>\n",
        "stderr": "",
        "exit_code": 0,
        "rewritten": {},
    },
}


class ReplayRecordingTest(unittest.TestCase):
    def setUp(self):
        path = mock.patch.dict(os.environ, {"PATH": f"{SORTING_AWAWA}{os.pathsep}{os.environ['PATH']}"})
        path.start()
        self.addCleanup(path.stop)

    def test_should_replay_the_run_ids_in_the_order_they_sorted_when_recorded(self):
        # Act
        outcome = replay_recording(self, RECORDING_OF_TWO_RUNS_OF_ONE_SECOND)

        # Assert
        self.assertEqual(outcome["stdout"], "ANSWER trees_<run_name:2>\nANSWER trees_<run_name:1>\n")
