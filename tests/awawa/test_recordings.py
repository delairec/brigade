import json
import unittest

from tests.awawa.provide_awawa import RECORDINGS, provide_awawa
from tests.awawa.replay_recording import replay_recording
from tests.process_launcher import ProcessLauncher


class TheRecordingsMatchTheAwawaOnThePathTest(unittest.TestCase):
    def setUp(self):
        provide_awawa(self)
        self.version = ProcessLauncher.run(
            ["awawa", "--version"],
            cwd="/",
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()

    def test_should_answer_every_recorded_call_as_it_was_recorded(self):
        for path in sorted(RECORDINGS.glob("*.json")):
            with self.subTest(recording=path.name):
                # Arrange
                recording = json.loads(path.read_text())

                # Act
                outcome = replay_recording(self, recording["call"])

                # Assert
                self.assertEqual(
                    outcome,
                    recording["outcome"],
                    f"{path.name} names {recording['version']}, awawa --version prints {self.version}",
                )
