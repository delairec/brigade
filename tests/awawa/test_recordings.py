import json
import subprocess
import unittest

from tests.awawa.provide_awawa import RECORDINGS, provide_awawa
from tests.awawa.replay_recording import replay_recording


class TheRecordingsMatchTheAwawaOnThePathTest(unittest.TestCase):
    def setUp(self):
        provide_awawa(self)
        self.version = subprocess.run(
            ["awawa", "--version"],  # noqa: S607 - the awawa on the PATH of the test, real or fake
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
