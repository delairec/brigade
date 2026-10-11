import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.awawa.provide_awawa import provide_awawa

SCRIPTED_AWAWA_DIRECTORY = Path(__file__).resolve().parent / "fixtures" / "scripted-awawa"
RECORDING_ASKED = "1"


class ProvideAwawaWhileRecordingTest(unittest.TestCase):
    def setUp(self):
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        self.root = Path(root.name)
        self.corpus = self.root / "corpus"
        self.corpus.mkdir()
        recordings = mock.patch("tests.awawa.provide_awawa.RECORDINGS", self.root / "recordings")
        recordings.start()
        self.addCleanup(recordings.stop)
        environment = mock.patch.dict(
            os.environ,
            {
                "PATH": f"{SCRIPTED_AWAWA_DIRECTORY}{os.pathsep}{os.environ['PATH']}",
                "AWAWA_RECORD": RECORDING_ASKED,
            },
        )
        environment.start()
        self.addCleanup(environment.stop)

    def test_should_have_the_real_awawa_answer_while_the_recordings_are_renewed(self):
        # Arrange
        provide_awawa(self)
        (self.corpus / "tasks.awawa").write_text("TASK  B1\n")

        # Act
        completed = subprocess.run(  # noqa: S603 - the test's own command line
            ["awawa", "fmt", str(self.corpus / "tasks.awawa")],  # noqa: S607 - the awawa provide_awawa put on PATH
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )

        # Assert
        self.assertEqual(
            [completed.stdout, completed.stderr, completed.returncode],
            [f"{self.corpus}/tasks.awawa\n", "1 file rewritten\n", 0],
        )
